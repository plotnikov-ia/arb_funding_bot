from src.stores import AccountDataStoreBinance

class AccountHandlerBinance:
    def __init__(self, store) -> None:
        self.store: AccountDataStoreBinance = store
    
    def handle_message(self, data):
        
        channel = data.get("e", "")
        
        if channel == "ACCOUNT_UPDATE":
            self.store.update_account(data=data)
        
        if channel == "ORDER_TRADE_UPDATE":
            self.store.update_order(data=data)
        
        # if channel == "TRADE_LITE":
        #     if not json_data["data"]["isSnapshot"]:
        #         self.store.update_fills(data=json_data)
        
        # if channel == "userNonFundingLedgerUpdates":
        #     if not json_data["data"]["isSnapshot"]:
        #         self.store.update_cash_flow(data=json_data)
                
                
                
### transfer from spot to perp
# {'e': 'ACCOUNT_UPDATE', 'T': 1776780116337, 'E': 1776780116338, 'a': {'B': [{'a': 'USDC', 'wb': '48.84650063', 'cw': '48.84650063', 'bc': '10'}], 'P': [], 'm': 'DEPOSIT'}}

### transfer from perp to spot
# {'e': 'ACCOUNT_UPDATE', 'T': 1776780134433, 'E': 1776780134434, 'a': {'B': [{'a': 'USDC', 'wb': '38.84650063', 'cw': '38.84650063', 'bc': '-10'}], 'P': [], 'm': 'WITHDRAW'}}

### funding fee
# b'{"e":"ACCOUNT_UPDATE","T":1776787203246,"E":1776787203246,"a":{"B":[{"a":"USDC","wb":"38.17806885","cw":"38.17806885","bc":"-0.00085067"}],"P":[],"m":"FUNDING_FEE"}}'

### create limit order
# {'e': 'ORDER_TRADE_UPDATE', 'T': 1776788790649, 'E': 1776788790650, 'o': {'s': 'ETHUSDC', 'c': 'web_coin_4y4b8mofbf7dqhq61p3paub', 'S': 'BUY', 'o': 'LIMIT', 'f': 'GTC', 'q': '0.02', 'p': '2313', 'ap': '0', 'sp': '0', 'x': 'NEW', 'X': 'NEW', 'i': 58846010837, 'l': '0', 'z': '0', 'L': '0', 'n': '0', 'N': 'USDC', 'T': 1776788790649, 't': 0, 'b': '46.26', 'a': '0', 'm': False, 'R': False, 'wt': 'CONTRACT_PRICE', 'ot': 'LIMIT', 'ps': 'BOTH', 'cp': False, 'rp': '0', 'pP': False, 'si': 0, 'ss': 0, 'V': 'EXPIRE_MAKER', 'pm': 'NONE', 'gtd': 0, 'er': '0'}}

### update limit order
# {'e': 'ORDER_TRADE_UPDATE', 'T': 1776789150137, 'E': 1776789150138, 'o': {'s': 'ETHUSDC', 'c': 'web_coin_px06wttcjgaebeca9w5ijo3', 'S': 'BUY', 'o': 'LIMIT', 'f': 'GTC', 'q': '0.02', 'p': '2315.9', 'ap': '0', 'sp': '0', 'x': 'AMENDMENT', 'X': 'NEW', 'i': 58846581664, 'l': '0', 'z': '0', 'L': '0', 'n': '0', 'N': 'USDC', 'T': 1776789150137, 't': 0, 'b': '46.318', 'a': '0', 'm': False, 'R': False, 'wt': 'CONTRACT_PRICE', 'ot': 'LIMIT', 'ps': 'BOTH', 'cp': False, 'rp': '0', 'pP': False, 'si': 0, 'ss': 0, 'V': 'EXPIRE_MAKER', 'pm': 'NONE', 'gtd': 0, 'er': '0'}}

### cancel limit order
# {'e': 'ORDER_TRADE_UPDATE', 'T': 1776789081389, 'E': 1776789081390, 'o': {'s': 'ETHUSDC', 'c': 'web_coin_3k0uxdsggnid0ax7zf16fvs', 'S': 'BUY', 'o': 'LIMIT', 'f': 'GTC', 'q': '0.02', 'p': '2310', 'ap': '0', 'sp': '0', 'x': 'CANCELED', 'X': 'CANCELED', 'i': 58846421973, 'l': '0', 'z': '0', 'L': '0', 'n': '0', 'N': 'USDC', 'T': 1776789081389, 't': 0, 'b': '0', 'a': '0', 'm': False, 'R': False, 'wt': 'CONTRACT_PRICE', 'ot': 'LIMIT', 'ps': 'BOTH', 'cp': False, 'rp': '0', 'pP': False, 'si': 0, 'ss': 0, 'V': 'EXPIRE_MAKER', 'pm': 'NONE', 'gtd': 0, 'er': '0'}}

### fill limit order
# {'e': 'TRADE_LITE', 'E': 1776789210247, 'T': 1776789210247, 's': 'ETHUSDC', 'q': '0.020', 'p': '2317.30', 'm': True, 'c': 'web_coin_px06wttcjgaebeca9w5ijo3', 'S': 'BUY', 'L': '2317.30', 'l': '0.020', 't': 702423109, 'i': 58846581664}
# {'e': 'ACCOUNT_UPDATE', 'T': 1776789210247, 'E': 1776789210247, 'a': {'B': [{'a': 'USDC', 'wb': '37.87866827', 'cw': '37.87866827', 'bc': '0'}], 'P': [{'s': 'ETHUSDC', 'pa': '0.02', 'ep': '2317.3', 'cr': '-0.28351998', 'up': '0.00586175', 'mt': 'cross', 'iw': '0', 'ps': 'BOTH', 'ma': 'USDC', 'bep': '2317.3'}], 'm': 'ORDER'}}
# {'e': 'ORDER_TRADE_UPDATE', 'T': 1776789210247, 'E': 1776789210247, 'o': {'s': 'ETHUSDC', 'c': 'web_coin_px06wttcjgaebeca9w5ijo3', 'S': 'BUY', 'o': 'LIMIT', 'f': 'GTC', 'q': '0.02', 'p': '2317.3', 'ap': '2317.3', 'sp': '0', 'x': 'TRADE', 'X': 'FILLED', 'i': 58846581664, 'l': '0.02', 'z': '0.02', 'L': '2317.3', 'n': '0', 'N': 'USDC', 'T': 1776789210247, 't': 702423109, 'b': '0', 'a': '0', 'm': True, 'R': False, 'wt': 'CONTRACT_PRICE', 'ot': 'LIMIT', 'ps': 'BOTH', 'cp': False, 'rp': '0', 'pP': False, 'si': 0, 'ss': 0, 'V': 'EXPIRE_MAKER', 'pm': 'NONE', 'gtd': 0, 'er': '0'}}