import itertools
import sys
import threading

import time
import json
from websocket import create_connection, WebSocketConnectionClosedException
from arbitrage import CryptoArbitrage

class Poloniex:

    def __init__(self):
        self.websocketUrl = 'wss://ws.poloniex.com/ws/public'
        self.graph = {}
        self.transactionFee = 0.2/100  # Taxa de transação de 0.2%

    def spinner(self, message="Procurando oportunidades"):
        """
        Gera um spinner de console ao lado de uma mensagem.
        """
        for spin_char in itertools.cycle(['-', '\\', '|', '/']):
            status = f"\r{message} {spin_char}"
            sys.stdout.write(status)
            sys.stdout.flush()
            time.sleep(0.1)

    def _getCurrentSymbols(self):
        payload = {
                "event": "subscribe",
                "channel": ["Ticker"],
                "symbols": ["all"] 
            }
        ws = create_connection(self.websocketUrl)
        ws.send(json.dumps(payload))
        responded = False
        while not responded:
            response = json.loads(ws.recv())
            if "data" in response:
                symbols = [data["symbol"] for data in response["data"]]
                responded = True
        ws.close()
        return symbols

    def _buildEmptyGraph(self):
        symbols = self._getCurrentSymbols()
        for symbol in symbols:
            base, quote = symbol.split('_')
            if base not in self.graph:
                self.graph[base] = {}
            if quote not in self.graph:
                self.graph[quote] = {}
            self.graph[base][quote] = 1
            self.graph[quote][base] = 1

    def _cleanGraph(self, currentSymbols):
        """Remove os nós obsoletos do grafo."""
        currentBases = set([symbol.split('_')[0] for symbol in currentSymbols])
        currentQuotes = set([symbol.split('_')[1] for symbol in currentSymbols])
        allCurrentSymbols = currentBases.union(currentQuotes)

        # Encontra os nós no grafo que não estão mais presentes nos símbolos atuais
        nodesToRemove = set(self.graph.keys()) - allCurrentSymbols
        
        # Remove os nós obsoletos
        for node in nodesToRemove:
            del self.graph[node]

        # Além disso, remove as conexões obsoletas
        for base in list(self.graph.keys()):
            for quote in list(self.graph[base].keys()):
                if f"{base}_{quote}" not in currentSymbols and f"{quote}_{base}" not in currentSymbols:
                    del self.graph[base][quote]

    def _updateGraph(self, orderBookData):
        for data in orderBookData:
            symbol = data['symbol']
            if symbol == "BTC_USDT":
                print("Ignoring BTC_USDT")

            base, quote = symbol.split('_')
            asks = data['asks']
            bids = data['bids']

            if len(asks) == 0 or len(bids) == 0:
                continue

            # Assume que o primeiro 'ask' e o primeiro 'bid' são os melhores preços disponíveis
            bestAskPrice = float(asks[0][0]) * (1 + self.transactionFee)  # Adiciona a taxa de transação ao preço de compra
            bestBidPrice = float(bids[0][0]) * (1 - self.transactionFee)  # Subtrai a taxa de transação do preço de venda

            # Atualiza o grafo com os preços de 'ask' e 'bid'
            if base not in self.graph:
                self.graph[base] = {}
            if quote not in self.graph:
                self.graph[quote] = {}
            
            # Aqui, estamos usando o preço de 'bid' para a conversão de base para quote
            # e o preço de 'ask' para a conversão de quote para base
            self.graph[base][quote] = bestBidPrice
            self.graph[quote][base] = 1 / bestAskPrice

    def checkArbitrageOpportunity(self):
        arb = CryptoArbitrage(self.graph)
        negative_cycle = arb.find_negative_cycle()
        if negative_cycle:
            profit = arb.calculate_profit(negative_cycle)
            if profit > 1.05:
                print(f'\nCycle Time {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
                print(f"Positive cycle: {negative_cycle}")
                print(f"% Profit: {profit}\n")
                with open('arbitrage.txt', 'a') as f:
                    f.write(f'Cycle Time {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}\n')
                    f.write(f"Positive cycle: {negative_cycle}\n")
                    f.write(f"% Profit: {profit}\n\n")
            # arb.plot_cycle_graph(negative_cycle)  # Opcional, se você quiser visualizar o ciclo
        else:
            sys.stdout.write('.')
            sys.stdout.flush()

    def subscribeOrderBook(self, symbols=["BTC_USDT"]):
        payload = {
            "event": "subscribe",
            "channel": ["book"],
            "symbols": symbols 
        }
        end_time = time.time() + 60  # Define um tempo de execução de 60 segundos

        while time.time() < end_time:
            try:
                ws = create_connection(self.websocketUrl)
                ws.send(json.dumps(payload))
                while time.time() < end_time:
                    response = json.loads(ws.recv())
                    if "data" in response:
                        self._updateGraph(response['data'])
                        self.checkArbitrageOpportunity()

            except WebSocketConnectionClosedException as e:
                print("WebSocket connection closed, trying to reconnect...")
                time.sleep(2)
    
    def run(self):
        while True:
            sys.stdout.write("\033[K")  # Limpa a linha do console
            currentSymbols = self._getCurrentSymbols()
            self._cleanGraph(currentSymbols)
            
            thread = threading.Thread(target=self.subscribeOrderBook, args=(currentSymbols,))
            thread.start()
            thread.join()

if __name__ == '__main__':
    poloniex = Poloniex()
    poloniex.run()