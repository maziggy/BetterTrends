![image](https://raw.githubusercontent.com/home-assistant/brands/refs/heads/master/custom_integrations/better_trends/logo.png)

# BetterTrends

A custom Home Assistant integration, that calculates trend values for entities and displays result in a nice way.

Currently only three entities are supported, but will change in the near future.

## Screenshot 

![image](https://raw.githubusercontent.com/maziggy/BetterTrends/refs/heads/main/screenshots/BetterTrends.png)

## How it works

* Add your existing entities to calculate trend for
  
![image](https://raw.githubusercontent.com/maziggy/BetterTrends/refs/heads/main/screenshots/BetterTrendsSetup.png)

* Entities data is fetched every (A) seconds
* If (B) entity data sets are fetched, trend is calculated and sensor.bettertrends_sensor_<your_entity> is updated.

![image](https://raw.githubusercontent.com/maziggy/BetterTrends/refs/heads/main/screenshots/BetterTrendsHelp.png)

* A: data fetch interval
* B: datasets fetched before calculating new trend value
* C: current datasets collected
* D: Total datasets required to calculate trend value (equals B)

You can click on A (interval), or B (steps) to change number.

## Installation

### Via HACS

1. Ensure you have [HACS](https://hacs.xyz/) installed.
2. In Home Assistant, go to **HACS** > **Frontend**.
3. Click the **"+"** button to add a new repository.
4. Enter the repository URL: `https://github.com/maziggy/BetterTrends.git`.
5. Select **Integration** as the category and **Save**.

or simply

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=maziggy&repository=BetterTrends&category=integration)

* Once installed, you'll get a persitant notification about how to add the two included dashboard cards (trend-card and trend-card-lite) to your resources.

![image](https://raw.githubusercontent.com/maziggy/BetterTrends/refs/heads/main/screenshots/BetterTrendsAddResource.png)

## Cards and options

### trend-card
```yaml
type: custom:trend-card
interval: number.bettertrends_interval
steps: number.bettertrends_steps
current_step: number.bettertrends_current_step
metric1_delta: sensor.bettertrends_<your_sensor_1>
metric1_name: <name>
metric2_delta: sensor.bettertrends_<your_sensor_2>
metric2_name: <name>
metric3_delta: sensor.bettertrends_<your_sensor_3>
metric3_name: <name>
theme:
  bgColor: "#2c2c2e"
  textColor: "#ffffff"
  iconColor: "#ff9e32"
  iconBgColor: "#323335"
  metricBgColor: "#323335"
  bubble1Color: "#1b7de5"
  bubble1TextColor: "#ffffff"
  value1TextColor: "#ffffff"
  bubble2Color: "#e7970d"
  bubble2TextColor: "#ffffff"
  value2TextColor: "#ffffff"
  bubble3Color: "#ab07ae"
  bubble3TextColor: "#ffffff"
  value3TextColor: "#ffffff"
  trendDownColor: "#498bff"
  trendEqualColor: "#4ff24b"
  trendUpColor: "#ff4c4c"
```

### trend-card-lite
```yaml
type: custom:trend-card-lite
metric1_delta: sensor.bettertrends_<your_sensor_1>
metric1_delta_name: <name>
metric2_delta: sensor.bettertrends_<your_sensor_2>
metric2_delta_name: <name>
metric3_delta: sensor.bettertrends_<your_sensor_3>
metric3_delta_name: <name>
theme:
  bgColor: "#2c2c2e"
  metricBgColor: "#212122"
  bubble1Color: "#2b8dd9"
  bubble1TextColor: "#ffffff"
  value1TextColor: "#ffffff"
  bubble2Color: "#e7970d"
  bubble2TextColor: "#ffffff"
  value2TextColor: "#ffffff"
  bubble3Color: "#ab07ae"
  bubble3TextColor: "#ffffff"
  value3TextColor: "#ffffff"
  trendDownColor: "#498bff"
  trendEqualColor: "#4ff24b"
  trendUpColor: "#ff4c4c"
```
