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

A: data fetch interval
B: datasets fetched before calculating new trend value
C: current datasets collected
D: Total datasets required to calculate trend value (euqals B)

You can click on A (interval), or B (steps) to change number.

