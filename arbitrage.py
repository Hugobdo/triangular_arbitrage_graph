import math
import networkx as nx
import matplotlib.pyplot as plt

class CryptoArbitrage:
    def __init__(self, graph):
        self.graph = graph
        self.converted_graph = self.add_fictitious_node(self.convert_to_negative_logs())

    def convert_to_negative_logs(self):
        converted_graph = {}
        for origin, destinations in self.graph.items():
            converted_graph[origin] = {}
            for destination, rate in destinations.items():
                converted_graph[origin][destination] = -math.log(rate)
        return converted_graph

    def add_fictitious_node(self, graph):
        # Adiciona um nó fictício com arestas de peso zero para todos os outros nós
        fictitious_node = "Fictitious"
        graph[fictitious_node] = {node: 0 for node in graph}
        return graph

    def find_negative_cycle(self):
        source = "Fictitious"  # Nó fictício
        distances = {node: float('inf') for node in self.converted_graph}
        predecessors = {node: None for node in self.converted_graph}
        distances[source] = 0

        # Bellman-Ford Algorithm
        for _ in range(len(self.converted_graph)):
            for origin in self.converted_graph:
                for destination, weight in self.converted_graph[origin].items():
                    if distances[origin] + weight < distances[destination]:
                        distances[destination] = distances[origin] + weight
                        predecessors[destination] = origin

        # Check for negative cycles
        for origin in self.converted_graph:
            for destination, weight in self.converted_graph[origin].items():
                if distances[origin] + weight < distances[destination]:
                    return self.reconstruct_negative_cycle(predecessors, destination)

        return None  # No negative cycle found

    def reconstruct_negative_cycle(self, predecessors, start_node):
        cycle = [start_node]
        current_node = start_node
        while True:
            next_node = predecessors[current_node]
            if next_node in cycle:
                cycle.append(next_node)
                cycle = cycle[cycle.index(next_node):]
                return cycle[::-1]
            cycle.append(next_node)
            current_node = next_node

    def calculate_profit(self, cycle):
        product_of_rates = 1
        org_dest_list = []
        for i in range(len(cycle) - 1):
            origin = cycle[i]
            destination = cycle[i + 1]
            rate = math.exp(-self.converted_graph[origin][destination])
            product_of_rates *= rate
            org_dest_list.append((origin, destination, rate, product_of_rates))
            
        if product_of_rates > 1.05:
            print("--------------------------------------------")
            print("Starting with 1 of the first:")
            for origin, destination, rate, product_of_rates in org_dest_list:
                print(f"{origin} -> {destination}: {rate:.6f} || Total -> {product_of_rates:.6f}")

        return product_of_rates

    def plot_cycle_graph(self, cycle):
        G = nx.DiGraph()

        # Adiciona as arestas do ciclo ao grafo
        for i in range(len(cycle) - 1):
            origin = cycle[i]
            destination = cycle[i + 1]
            rate = math.exp(-self.converted_graph[origin][destination])
            G.add_edge(origin, destination, weight=rate)
        
        # Se o ciclo é um loop, conectar o último ao primeiro
        if cycle[0] != cycle[-1]:
            origin = cycle[-1]
            destination = cycle[0]
            rate = math.exp(-self.converted_graph[origin][destination])
            G.add_edge(origin, destination, weight=rate)

        pos = nx.spring_layout(G)  # Posicionamento dos nós

        # Desenha o grafo
        nx.draw(G, pos, with_labels=True, node_size=2000, node_color="lightblue", edge_color="black", width=2, font_size=10, font_weight="bold")

        # Desenha os pesos das arestas
        edge_labels = {(u, v): f"{d['weight']:.6f}" for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red')

        plt.title("Ciclo de Arbitragem de Moeda")
        plt.axis('off')
        plt.show()

if __name__ == "__main__":
    # Grafo de teste
    graph = {
        'GBP': {'USD': 1.27, 'AUD': 1.82},
        'USD': {'AUD': 1.43, 'NZD': 1.51, 'GBP': 0.79},
        'AUD': {'GBP': 0.55, 'USD': 0.7, 'NZD': 1.05},
        'NZD': {'AUD': 0.95, 'USD': 0.66}
    }
            
    arb = CryptoArbitrage(graph)
    negative_cycle = arb.find_negative_cycle()
    if negative_cycle:
        profit = arb.calculate_profit(negative_cycle)
        print(f"Negative cycle: {negative_cycle}")
        print(f"Profit: {profit}")
    else:
        print("No negative cycle found.")

    arb.plot_cycle_graph(negative_cycle)