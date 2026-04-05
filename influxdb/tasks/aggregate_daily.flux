// Task: aggregate_daily
//
// Aggregiert Stundenwerte (Bucket "hourly") in Tageswerte (Bucket "daily").
//
// Pro Sensor werden geschrieben:
//   daily_kwh  — Tagesenergie in kWh  (sum der stündlichen energy_wh ÷ 1000)
//   mean_w     — Tagesdurchschnitt der mittleren Stundenleistung
//
// Zusätzlich werden drei abgeleitete Tageskennzahlen geschrieben (Measurement "derived"):
//   self_consumption_kwh    — Eigenverbrauch = Erzeugung − Netzeinspeisung
//   self_consumption_rate   — Eigenverbrauchsquote in % (Eigenverbrauch ÷ Erzeugung × 100)
//   autarky_rate            — Autarkiegrad in % (Eigenverbrauch ÷ Gesamtverbrauch × 100)
//
// Sensoren für die Kennzahlen (aus ModbusConfig):
//   Erzeugung PV  → sum_pv_power_inverter_dc
//   Einspeisung   → grid_power_total  (positiv = Einspeisung ins Netz)
//   Gesamtverbrauch → home_consumption
//
// Installation:
//   influx task create --file aggregate_daily.flux

option task = {
    name: "aggregate_daily",
    every: 1d,
    offset: 15m,   // 15 Minuten nach Mitternacht, damit alle Stundenwerte im Bucket sind
}

// ── 1. Basis-Aggregation: alle Sensoren ────────────────────────────────────

hourly_data = from(bucket: "hourly")
    |> range(start: -1d)
    |> filter(fn: (r) => r._measurement == "energy")

// Tagesenergie in kWh (nur sinnvoll für W-Sensoren, wird aber für alle berechnet)
daily_kwh = hourly_data
    |> filter(fn: (r) => r._field == "energy_wh")
    |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)
    |> map(fn: (r) => ({r with _field: "daily_kwh", _value: r._value / 1000.0}))

// Tagesdurchschnitt der mittleren Stundenleistung
daily_mean = hourly_data
    |> filter(fn: (r) => r._field == "mean_w")
    |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
    |> map(fn: (r) => ({r with _field: "mean_w"}))

union(tables: [daily_kwh, daily_mean])
    |> to(bucket: "daily", org: "pvmonitor")

// ── 2. Abgeleitete Kennzahlen ───────────────────────────────────────────────
//
// Vorzeichenkonvention Kostal:
//   grid_power_total > 0  → Einspeisung ins Netz
//   grid_power_total < 0  → Bezug aus dem Netz
//
// Für Tageskennzahlen werden nur die positiven Einspeisstunden summiert.
// Nur Stunden, in denen PV erzeugt hat (energy_wh > 0), gehen in die Quote ein.

pv_generation = from(bucket: "hourly")
    |> range(start: -1d)
    |> filter(fn: (r) =>
        r._measurement == "energy"
        and r.sensor == "sum_pv_power_inverter_dc"
        and r._field == "energy_wh"
    )
    |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)

// Einspeisung: nur positive Werte (Netzeinspeisung)
grid_feed = from(bucket: "hourly")
    |> range(start: -1d)
    |> filter(fn: (r) =>
        r._measurement == "energy"
        and r.sensor == "grid_power_total"
        and r._field == "energy_wh"
        and r._value > 0.0
    )
    |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)

home_consumption = from(bucket: "hourly")
    |> range(start: -1d)
    |> filter(fn: (r) =>
        r._measurement == "energy"
        and r.sensor == "home_consumption"
        and r._field == "energy_wh"
    )
    |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)

// Eigenverbrauch = Erzeugung − Einspeisung
self_consumption = join(
    tables: {gen: pv_generation, feed: grid_feed},
    on: ["_time", "sensor"],
)
    |> map(fn: (r) => ({
        _time: r._time,
        _measurement: "derived",
        _field: "self_consumption_kwh",
        _value: (r._value_gen - r._value_feed) / 1000.0,
    }))
    |> to(bucket: "daily", org: "pvmonitor")

// Eigenverbrauchsquote = Eigenverbrauch ÷ Erzeugung × 100
self_consumption_rate = join(
    tables: {gen: pv_generation, feed: grid_feed},
    on: ["_time", "sensor"],
)
    |> map(fn: (r) => ({
        _time: r._time,
        _measurement: "derived",
        _field: "self_consumption_rate",
        // avoid division by zero on days with no generation
        _value: if r._value_gen > 0.0
            then (r._value_gen - r._value_feed) / r._value_gen * 100.0
            else 0.0,
    }))
    |> to(bucket: "daily", org: "pvmonitor")

// Autarkiegrad = Eigenverbrauch ÷ Gesamtverbrauch × 100
autarky = join(
    tables: {gen: pv_generation, feed: grid_feed, cons: home_consumption},
    on: ["_time", "sensor"],
)
    |> map(fn: (r) => ({
        _time: r._time,
        _measurement: "derived",
        _field: "autarky_rate",
        _value: if r._value_cons > 0.0
            then (r._value_gen - r._value_feed) / r._value_cons * 100.0
            else 0.0,
    }))
    |> to(bucket: "daily", org: "pvmonitor")
