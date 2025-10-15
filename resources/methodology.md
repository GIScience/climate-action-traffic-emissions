## Input data

The following input data is used:
* OpenStreetMap (OSM) road network
* [Average daily traffic volume (ADTV) of Berlin 2019](https://gdi.berlin.de/geonetwork/srv/ger/catalog.search#/metadata/125b728c-3ef9-49fd-94c5-24b2143ede2b), obtained from the Geoportal of the city of Berlin
* [Population grid from Global Human Settlement Layer](https://human-settlement.emergency.copernicus.eu/download.php?ds=pop)
* Speed-dependent fuel consumption equations ([Sobrino et al. 2014, Table 3](https://doi.org/10.1007/s11067-014-9225-y)).
* Emission factors from COPERT ([EMEP/EEA air pollutant emission inventory guidebook 2023 – Update 2024, Tables 3-6 and 3-12](https://copert.emisia.com/wp-content/uploads/2024/07/1.A.3.b.i-iv-Road-transport-2024.pdf))
* Market shares of cars by fuel type ([Kraftfahrt-Bundesamt](https://www.kba.de/DE/Statistik/Fahrzeuge/Bestand/Umwelt/2024/2024_b_umwelt_tabellen.html?nn=3525028&fromStatistic=3525028&yearFilter=2024&fromStatistic=3525028&yearFilter=2024))
* Market shares of different vehicle types ([Kraftfahrt-Bundesamt](https://www.kba.de/DE/Statistik/Fahrzeuge/Bestand/FahrzeugklassenAufbauarten/2024/2024_b_fzkl_tabellen.html))

## Traffic volume estimation

### Model development

In the first step, we derive the average daily traffic volume (ADTV) for every combination of OpenStreetMap (OSM) road type and number of lanes in Berlin, Germany.
To this end, we first obtain the road network of Berlin from OSM, including the attributes **Road type** and **Number of lanes**.
Next, we join the ADTV of Berlin from 2019 to the road network.
Next, the Berlin road network is split into a training and testing set (50:50).
For the training set, the ADTV is calculated for each combination of highway type and number of lanes.
These ADTVs are then assigned to all OSM road segments based on their highway type and number of lanes.
To validate the accuracy, the assigned ADTVs are compared to the observed ADTVs in the testing set.

### Apply estimation to selected area

In the second step, the ADTVs that have been derived for each combination of OSM road type and number of lanes in Berlin are assigned to the OSM road network in the selected area based on their highway type and number of lanes.
The assigned ADTVs are scaled by the population density and the road length per capita in the selected area.
This is based on the assumption that traffic volume increases with population density and decreases with road length per capita.
The information on the population density is taken from the population grid of the Global Human Settlement Layer.


## Traffic emission estimation

The estimation of annual road traffic CO₂, CO, and NOx emissions for each road segment is done using the following formula:

E = ADTV * FC_speed * EF / 1000000 * 365

    E: Emissions [t per road-km per year]

    ADTV: Average daily traffic volume (number of vehicles per day)

    FC_speed: Speed-dependent fuel consumption [l/veh-km]

    EF: Fuel emission factor [g/l fuel]

For road segments with speed limit information in OSM, the speed-dependent fuel consumption is calculated using equations derived from [Sobrino et al. (2014)](https://doi.org/10.1007/s11067-014-9225-y), Table 3 - passenger car:

| Vehicle Type       | Fuel Consumption Function (g fuel / veh-km) |
|--------------------|------------------------------------------------------------------|
| Motorcycle         | FC = 25.722 + (276.13 / V) + (−0.254)·V + 0.00311·V²             |
| Passenger Car      | FC = 54.7 + (496 / V) + (−0.542)·V + 0.0042·V²                   |
| Light-Duty Vehicle | FC = 146.27 + ((−0.0000106) / V) + (−2.596)·V + 0.01984·V²       |
| Rigid Truck        | FC = 152.96 + (604.156 / V) + (−2.295)·V + 0.0238·V²             |
| Articulated Truck  | FC = 332.603 + (1680.879 / V) + (−4.676)·V + 0.0311·V²           |
| Bus                | FC = 281.735 + (4186.178 / V) + (−3.457)·V + 0.0216·V²           |

The speed-dependent fuel consumption is further weighted by the market shares of the different vehicle types in Germany:

| Vehicle Type       | Market Share |
|--------------------|--------------|
| Petrol car         | 0.534        |
| Diesel car         | 0.25         |
| Motorcycle         | 0.082        |
| Bus                | 0.001        |
| Rigid truck        | 0.062        |
| Articulated truck  | 0.004        |
| Other              | 0.042        |

For roads without speed limit information, we assume fixed traveling speeds. Using the fuel consumption functions above, this leads us to the following emission factors for roads without speed information:

| Road type                        | Speed [km/h] | g CO₂ / veh-km | g CO / veh-km | g NOx / veh-km |
|----------------------------------|--------------|-------------------|------------------|-------------------|
| Motorways                        | 120          | 203.64            | 1.25             | 0.52              |
| Roads outside of built-up areas  | 70           | 153.69            | 0.94             | 0.39              |
| Roads inside of built-up areas   | 30           | 196.91            | 1.20             | 0.50              |


## Limitations

To obtain the ADTVs for the selected area, we scale the ADTVs for Berlin by the population density and the road length per capita in the selected area.
While there are better proxies for traffic volume than population density, such as car ownership rates and income (Ingram & Liu 1997), we use population density, because this data is more easily available at high spatial resolution and coverage.

During the estimation of traffic emissions, we assume that the traveling speed is constant and equal to the speed limit.
The impact of traffic lights, congestion, or vehicles exceeding the speed limit is not accounted for.
In most cases, this means that we are probably underestimating the emissions.
For roads without speed limit information, we assume fixed traveling speeds, which at best represent average values and do not account for the actual road and traffic conditions.
Differences between the actual vehicle fleet composition and our assumed fleet composition may lead to additional over- or underestimation of the emission estimates.


## OSM Tags used in the download of the OSM road network
- **Road type**: Tagged as [`highway=*`](https://wiki.openstreetmap.org/wiki/Key:highway) with values including: [`motorway`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dmotorway), [`trunk`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dtrunk), [`primary`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dprimary), [`secondary`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dsecondary), [`tertiary`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dtertiary), [`residential`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dresidential), [`living_street`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dliving_street), and [`unclassified`](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dunclassified).
- **Number of lanes**: Tagged as [`lanes=*`](https://wiki.openstreetmap.org/wiki/Lanes).
- **Speed limit**: Tagged as [`maxspeed=*`](https://wiki.openstreetmap.org/wiki/Key:maxspeed).