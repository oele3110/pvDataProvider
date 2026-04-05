// Task: aggregate_hourly
//
// Aggregiert Rohdaten (1s-Auflösung, Bucket "raw") in Stundenwerte (Bucket "hourly").
//
// Pro Sensor und Stunde werden vier Felder geschrieben:
//   energy_wh  — Energie in Wh  (sum(W) × 1s ÷ 3600 = Wh, nur sinnvoll für W-Sensoren)
//   mean_w     — Durchschnittliche Leistung / Messwert in der Stunde
//   min_w      — Minimum in der Stunde
//   max_w      — Maximum in der Stunde
//
// Installation (InfluxDB UI → Tasks → + Create Task → Import):
//   Variablen anpassen: org muss mit config.yaml übereinstimmen.
//
// Installieren per CLI:
//   influx task create --file aggregate_hourly.flux

option task = {
    name: "aggregate_hourly",
    every: 1h,
    offset: 5m,    // 5 Minuten nach der vollen Stunde starten, damit alle Daten im Bucket sind
}

data = from(bucket: "raw")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "energy")

// Energie: Summe aller W-Momentanwerte × 1s ÷ 3600 = Wh
// (Bei 1 Datenpunkt pro Sekunde und 3600 Punkten pro Stunde: sum/3600 = Wh)
energy = data
    |> aggregateWindow(every: 1h, fn: sum, createEmpty: false)
    |> map(fn: (r) => ({r with _field: "energy_wh", _value: r._value / 3600.0}))

mean_val = data
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    |> map(fn: (r) => ({r with _field: "mean_w"}))

min_val = data
    |> aggregateWindow(every: 1h, fn: min, createEmpty: false)
    |> map(fn: (r) => ({r with _field: "min_w"}))

max_val = data
    |> aggregateWindow(every: 1h, fn: max, createEmpty: false)
    |> map(fn: (r) => ({r with _field: "max_w"}))

union(tables: [energy, mean_val, min_val, max_val])
    |> to(bucket: "hourly", org: "pvmonitor")
