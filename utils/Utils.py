def process_sensor_value(result, config):
    if "factor" in config:
        result = result * config["factor"]
    if "digits_round" in config:
        digits_round = config["digits_round"]
        result = round(result, digits_round)
        if digits_round == 0:
            result = int(result)
    return result
