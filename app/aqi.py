import numpy as np

def calculate_us_aqi(pollutants):
    def aqi_formula(c, c_low, c_high, iaqi_low, iaqi_high):
        return ((iaqi_high - iaqi_low) / (c_high - c_low)) * (c - c_low) + iaqi_low

    us_aqi_breakpoints = {
        'pm25': [
            (0, 12.0, 0, 50),
            (12.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, float('inf'), 301, 500)
        ],
        'pm10': [
            (0, 54, 0, 50),
            (55, 154, 51, 100),
            (155, 254, 101, 150),
            (255, 354, 151, 200),
            (355, 424, 201, 300),
            (425, float('inf'), 301, 500)
        ],
        'o3': [
            (0, 54, 0, 50),
            (55, 70, 51, 100),
            (71, 85, 101, 150),
            (86, 105, 151, 200),
            (106, 200, 201, 300),
            (201, float('inf'), 301, 500)
        ],
        'no2': [
            (0, 53, 0, 50),
            (54, 100, 51, 100),
            (101, 360, 101, 150),
            (361, 649, 151, 200),
            (650, 1249, 201, 300),
            (1250, float('inf'), 301, 500)
        ],
        'co': [
            (0, 4.4, 0, 50),
            (4.5, 9.4, 51, 100),
            (9.5, 12.4, 101, 150),
            (12.5, 15.4, 151, 200),
            (15.5, 30.4, 201, 300),
            (30.5, float('inf'), 301, 500)
        ],
        'so2': [
            (0, 35, 0, 50),
            (36, 75, 51, 100),
            (76, 185, 101, 150),
            (186, 304, 151, 200),
            (305, 604, 201, 300),
            (605, float('inf'), 301, 500)
        ]
    }
    iaqis = {}
    for pollutant, concentration in pollutants.items():
        if pollutant not in us_aqi_breakpoints:
            raise ValueError(f"unknown pollutant: {pollutant}")

        for (c_low, c_high, iaqi_low, iaqi_high) in us_aqi_breakpoints[pollutant]:
            if c_low <= concentration <= c_high:
                iaqis[pollutant] = aqi_formula(concentration, c_low, c_high, iaqi_low, iaqi_high)
                break
        else:
            if concentration < us_aqi_breakpoints[pollutant][0][0]:
                iaqis[pollutant] = us_aqi_breakpoints[pollutant][0][2]
            elif concentration > us_aqi_breakpoints[pollutant][-1][1]:
                iaqis[pollutant] = us_aqi_breakpoints[pollutant][-1][3]

    return max(iaqis.values())




def calculate_iaqi(concentration, pollutant):
    cn_aqi_breakpoints = {
        'pm25': [
            (0, 50, 0, 35),       # (IAQI_low, IAQI_high, Conc_low, Conc_high)
            (51, 100, 35, 75),
            (101, 150, 75, 115),
            (151, 200, 115, 150),
            (201, 300, 150, 250),
            (301, 500, 250, 500)
        ],
        'pm10': [
            (0, 50, 0, 50),
            (51, 100, 50, 150),
            (101, 150, 150, 250),
            (151, 200, 250, 350),
            (201, 300, 350, 420),
            (301, 500, 420, 600)
        ],
        'so2': [
            (0, 50, 0, 50),
            (51, 100, 50, 150),
            (101, 150, 150, 475),
            (151, 200, 475, 800),
            (201, 300, 800, 1600),
            (301, 500, 1600, 2100)
        ],
        'no2': [
            (0, 50, 0, 40),
            (51, 100, 40, 80),
            (101, 150, 80, 180),
            (151, 200, 180, 280),
            (201, 300, 280, 565),
            (301, 500, 565, 750)
        ],
        'o3': [
            (0, 50, 0, 100),
            (51, 100, 100, 160),
            (101, 150, 160, 215),
            (151, 200, 215, 265),
            (201, 300, 265, 800),
            (301, 500, 800, 1000)
        ],
        'co': [
            (0, 50, 0, 2),
            (51, 100, 2, 4),
            (101, 150, 4, 14),
            (151, 200, 14, 24),
            (201, 300, 24, 36),
            (301, 500, 36, 48)
        ]
    }
    breakpoints = cn_aqi_breakpoints.get(pollutant)
    if not breakpoints:
        raise ValueError(f"unknown pollutant: {pollutant}")

    for (aqi_low, aqi_high, conc_low, conc_high) in breakpoints:
        if conc_low <= concentration <= conc_high:
            iaqi = ((aqi_high - aqi_low) / (conc_high - conc_low)) * (concentration - conc_low) + aqi_low
            return iaqi

    aqi_low, aqi_high, conc_low, conc_high = breakpoints[-1]
    iaqi = ((aqi_high - aqi_low) / (conc_high - conc_low)) * (concentration - conc_low) + aqi_low
    return iaqi

def calculate_cn_aqi(pollutants):
    iaqis = []

    for pollutant, concentration in pollutants.items():
        if concentration is not None:
            try:
                iaqi = calculate_iaqi(concentration, pollutant)
                iaqis.append(iaqi)
            except ValueError as e:
                print(f"error values: {e}")
                continue

    aqi = max(iaqis)
    return aqi