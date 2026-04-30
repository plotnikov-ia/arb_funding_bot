def calc_distance(
    ask_price: float,
    mid_price: float,
    bid_price: float
) -> (float, float):
    total_distance = ask_price - bid_price
    to_end_distance = abs(ask_price - mid_price)
    to_ask_percent = (to_end_distance / total_distance) * 100.0
    to_start_distance = abs(mid_price - bid_price)
    to_bid_percent = (to_start_distance / total_distance) * 100.0
    return to_ask_percent, to_bid_percent
