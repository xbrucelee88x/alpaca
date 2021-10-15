
#https://alpaca.markets/learn/swell-socially-responsible-investing/

"""
Do-it-yourself passive socially responsible investing example algo
Author: evan@alpaca.markets
Notes:
*New SRI portfolio only accurate when run during regular trading hours
*All orders submitted are MARKET DAY orders
*Tries to obtain thematic allocations as close as possible to desired
*Minimum account balance you'll need to use this algo is enough to buy at least 1 share of each of your desired thematic exposures
*Generally speaking, the allocation model works better with at least $1,000 and improves as even larger amounts are invested
*Liquidating orders in non-thematic stocks to free up capital when necessary to fulfill the desired allocation
are in no particular order and will liquidate the entire position before evaluating whether or not to liquidate another.
*Algo is for illustrative purposes only and is not a recommendation to buy or sell a security.
"""

import argparse
import math
import alpaca_trade_api as ata

SYMBOL_MAP = {'diversified':["Diversified SRI","USSG"],
              'water':["Clean Water","PHO"],
              'energy':["Renewable Energy","ICLN"],
              'health':["Healthy Living","BFIT"],
              'disease':["Disease Eradication","XBI"],
              'gender':["Gender Diversity","SHE"]}

def print_acct(positions,equity,themes):
    print("Theme                | Symbol | Qty    | Market Value | % of Portfolio ")
    print("-----------------------------------------------------------------------")
    for t in themes:
        if t.target==0:
            print("%-20s | %-6s | %-6s | %-12s | %-14s" % (t.name, "0", "0", "0", "0"))
        else:
            for p in positions:
                if t.symbol == p.symbol:
                    print("%-20s | %-6s | %-6s | %-12s | %-14s" % (t.name,p.symbol,p.qty, p.market_value, round(float(p.market_value)/float(equity)*100,2)))
                    break

class Theme():
    def __init__(self,name,alloc,symbol,price,amount):
        self.name = name
        self.symbol = symbol
        self.ref_price = price
        self.target = alloc/100.0
        self.shares = math.floor((amount*self.target)/self.ref_price)
        self.value = self.shares*self.ref_price
        self.actual = round(self.value/amount,4)
        self.order = []


def main(args):
    #initialize
    api = ata.REST(key_id='<your key id>', secret_key='<your secret key>',base_url='https://api.alpaca.markets', api_version='v2')
    acct = api.get_account()
    equity = float(acct.equity)
    positions = api.list_positions()
    if args.amount:
        amount = int(args.amount)
    else:
        amount = float(equity)

    print("\nAmount to allocate/rebalance:", amount)
    print("Account equity:", equity)

    a_sum = 0
    orders = []
    themes = []
    symbols = []

    #build each theme and order
    for arg in vars(args):
        if arg in SYMBOL_MAP:
            symbol = SYMBOL_MAP[arg][1]
            symbols += [symbol]
            name = SYMBOL_MAP[arg][0]
            alloc = vars(args)[arg]
            a_sum += alloc
            bars = api.get_barset(symbol,'minute',limit=10)
            price = bars[symbol][-1].c * 1.04
            theme = Theme(name, alloc, symbol, price, amount)
            #initialize order assuming no existing position
            theme.order = ["buy", theme.shares, theme.symbol, theme.value]
            themes += [theme]
            # check existing positions to determine qty to buy/sell for rebalance
            for p in positions:
                if symbol == p.symbol:
                    qty = theme.shares - int(p.qty)
                    if qty < 0:
                        theme.order = ["sell", abs(qty), theme.symbol, qty*theme.ref_price]
                    else:
                        theme.order = ["buy", qty, theme.symbol, qty*theme.ref_price]
                    break
            if theme.order[1]!=0:
                orders += [theme.order]
    assert a_sum <= 100, "Sum of allocations exceeds 100%"

    #output current SRI state
    print("\nCurrent SRI Portfolio")
    print_acct(positions,equity,themes)

    #generate liquidating orders in other holdings if necessary to free up cash
    approx_value_to_buy = sum(o[3] for o in orders)
    portfolio_value = float(acct.long_market_value) + abs(float(acct.short_market_value))
    portfolio_avail = equity - portfolio_value
    print("\nValue of all holdings:",portfolio_value)
    if portfolio_avail < approx_value_to_buy:
        deficit = round(approx_value_to_buy - portfolio_avail,2)
        print("Need to free up %s to rebalance." %deficit)
        for p in positions:
            if p.symbol not in symbols:
                print("\nSubmitting liquidating orders...")
                if deficit>0:
                    q = int(p.qty)
                    if q<0:
                        print('%s %s %s' % ("buy", abs(q), p.symbol))
                        api.submit_order(symbol=p.symbol, qty=abs(q), side="buy", type='market', time_in_force='day')
                    if q>0:
                        print('%s %s %s' % ("sell", q, p.symbol))
                        api.submit_order(symbol=p.symbol, qty=q, side="sell", type='market', time_in_force='day')
                    b = api.get_barset(p.symbol, 'minute', limit=10)
                    p = b[p.symbol][-1].c * 1.04
                    mv = round(abs(p*q),2)
                    deficit -= mv
                    if deficit>0:
                        print("Still need to free up %s to rebalance." %deficit)
                    else:
                        print("Done freeing up funds to invest.")

    #output thematic rebalance orders and final account state
    print("\nSubmitting orders...")
    for o in orders:
        print('%s %s %s' %(o[0],o[1],o[2]))
        api.submit_order(symbol=o[2], qty=o[1], side=o[0], type='market', time_in_force='day')
    print("\nNew SRI Portfolio")
    equity = api.get_account().equity
    print_acct(api.list_positions(),equity,themes)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--amount', help='$ amount to allocate, if no value specified then uses current account equity')
    parser.add_argument('--diversified', type=int, help='% alloc to Diversified SRI(high ESG performance)', required=True)
    parser.add_argument('--water', type=int, help='% alloc to Clean Water', required=True)
    parser.add_argument('--energy', type=int, help='% alloc to Renewable Energy', required=True)
    parser.add_argument('--health', type=int, help='% alloc to Healthy Living', required=True)
    parser.add_argument('--disease', type=int, help='% alloc to Disease Eradication', required=True)
    parser.add_argument('--gender', type=int, help='% alloc to Gender Diversity', required=True)
    args = parser.parse_args()
    main(args)
