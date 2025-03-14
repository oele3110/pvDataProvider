from modbusReader.ModbusDataType import ModbusDataType

modbus_config = {
    "grid_power_total": {
        "address": 40972,
        "type": ModbusDataType.INT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Grid Power Total",
        "unit": "W"
    },
    "sum_output_inverter_ac": {
        "address": 40974,
        "type": ModbusDataType.INT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum output inverter AC",
        "unit": "W"
    },
    "sum_pv_power_inverter_dc": {
        "address": 40976,
        "type": ModbusDataType.INT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum PV power inverter DC",
        "unit": "W"
    },
    "home_consumption": {
        "address": 40982,
        "type": ModbusDataType.INT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Home Consumption",
        "unit": "W"
    },
    "sum_battery_charge_discharge_dc": {
        "address": 40984,
        "type": ModbusDataType.INT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum battery charge / discharge DC",
        "unit": "W"
    },
    "system_state_of_charge": {
        "address": 40986,
        "type": ModbusDataType.UINT16,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "System state of charge",
        "unit": "%"
    },
    "home_consumption_from_pv": {
        "address": 40988,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Home consumption from PV",
        "unit": "W"
    },
    "home_consumption_from_battery": {
        "address": 40990,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Home consumption from battery",
        "unit": "W"
    },
    "home_consumption_from_grid": {
        "address": 40992,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Home consumption from grid",
        "unit": "W"
    },
    "active_charge_mode": {
        "address": 40994,
        "type": ModbusDataType.UINT16,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Active charge mode",
        "unit": ""
    },
    "sum_wallbox_charge_power_total": {
        "address": 40996,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum wallbox charge power total",
        "unit": "W"
    },
    "sum_wallbox_charge_power_pv": {
        "address": 40998,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum wallbox charge power PV",
        "unit": "W"
    },
    "sum_wallbox_charge_power_battery": {
        "address": 41000,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum wallbox charge power battery",
        "unit": "W"
    },
    "sum_wallbox_charge_power_grid": {
        "address": 41002,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum wallbox charge power grid",
        "unit": "W"
    },
    "sum_inverter_control_values": {
        "address": 41004,
        "type": ModbusDataType.UINT32,
        "resolution": 1,
        "digits_round": 0,
        "update_frequency": 1,
        "display_string": "Sum inverter control values",
        "unit": "W"
    }
}
