# BetterTrends

A custom Home Assistant integration, that calculates trend values for entities and displays result in a nice way.

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
* D: Total datasets required to calculate trend value (euqals B)

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

