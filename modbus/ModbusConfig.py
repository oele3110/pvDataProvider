from modbusReader.ModbusDataType import ModbusDataType

modbus_config = {
    "home_consumption":
        {
            "address": 40982,
            "type": ModbusDataType.UINT32,
            "resolution": 1,
            "digits_round": 0,
            "update_frequency": 1,
            "display_string": "Home Consumption",
            "unit": "W"
        }
}
