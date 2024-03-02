import requests
import time
import json
from websocket import create_connection, WebSocketConnectionClosedException
from arbitrage import CryptoArbitrage

class Poloniex:

    def __init__(self):
        self.pricesUrl = 'https://api.poloniex.com/markets/price'
        self.websocketUrl = 'wss://ws.poloniex.com/ws/public'
        self.graph = {}
        self.transactionFee = 0.002

    def getPrices(self):
        response = requests.get(self.pricesUrl).json()
        tsLimit = self.minimumTimestamp()
        tickerPrices = []
        for item in response:
            if item['ts'] > tsLimit:
                tickerPrices.append({'symbol': item['symbol'], 'price': float(item['price'])})
        return tickerPrices
    
    def minimumTimestamp(self):
        return time.time()*1000 - 450000  # Ajustado para 7 minutos atrás

    def getGraph(self):
        tickerPrices = self.getPrices()
        for item in tickerPrices:
            base, quote = item['symbol'].split('_')
            price = item['price'] * (1 - self.transactionFee)
            if base not in self.graph:
                self.graph[base] = {}
            if quote not in self.graph:
                self.graph[quote] = {}
            self.graph[base][quote] = price
            self.graph[quote][base] = 1 / price

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
            print(f'Cycle Time {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
            print("No arbitrage opportunity found.\n")
            
    def updateGraphWithClosePrice(self, symbol, close_price):
        base, quote = symbol.split('_')
        price = close_price * (1 - self.transactionFee)
        if base not in self.graph:
            self.graph[base] = {}
        if quote not in self.graph:
            self.graph[quote] = {}
        self.graph[base][quote] = price
        self.graph[quote][base] = 1 / price
    
    def getCurrentSymbols(self):
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

    def subscribeTicker(self, symbols=["all"]):
        payload = {
            "event": "subscribe",
            "channel": ["Ticker"],
            "symbols": symbols 
        }

        while True:  # Loop infinito para tentar reconectar sempre
            try:
                ws = create_connection(self.websocketUrl)
                ws.send(json.dumps(payload))
                while True:
                    response = json.loads(ws.recv())
                    if "data" in response:  # Verifica se a chave 'data' está na resposta
                        for data in response["data"]:
                            symbol = data["symbol"]
                            close_price = float(data["close"])
                            self.updateGraphWithClosePrice(symbol, close_price)
                        self.checkArbitrageOpportunity()
                    time.sleep(1)

            except WebSocketConnectionClosedException as e:
                print("WebSocket connection closed, trying to reconnect...")
                time.sleep(2)  # Espera um pouco antes de tentar reconectar

            except Exception as e:
                print(f"An error occurred: {e}")
                ws.close()
                break  # Sai do loop após um erro desconhecido
    
    def subscribeOrderBook(self, symbols=["BTC_USDT"]):
        payload = {
            "event": "subscribe",
            "channel": ["book"],
            "symbols": symbols 
        }

        while True:
            try:
                ws = create_connection(self.websocketUrl)
                ws.send(json.dumps(payload))
                while True:
                    response = json.loads(ws.recv())
                    if "data" in response:
                        print(response)
                    time.sleep(1)

            except WebSocketConnectionClosedException as e:
                print("WebSocket connection closed, trying to reconnect...")
                time.sleep(2)
        
if __name__ == '__main__':
    poloniex = Poloniex()
    poloniex.subscribeOrderBook(['BTS_BTC', 'DASH_BTC', 'DOGE_BTC'])