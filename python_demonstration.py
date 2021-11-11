# ~~~~~
# SETUP
# ~~~~~

# Import libraries
import json, requests, datetime, decouple, psycopg2, webbrowser
import matplotlib.pyplot as plt

# Path and name for area of interest (AOI)
aoi_path = "demo/aoi.geojson"

# Planet API address and key
api_address = 'https://api.planet.com/data/v1/quick-search'
api_key = decouple.config('PLANET_API_KEY')

# Time interval for Planet imagery
today = datetime.datetime.now()
lastWeek = today - datetime.timedelta(days=7)


# ~~~~~~~~~~~~~~~~
# STEP 1: DRAW AOI
# ~~~~~~~~~~~~~~~~

aoi_name = 'lagos'

# ~~~~~~~~~~~~~~~~~~~
# STEP 2: READ IN AOI
# ~~~~~~~~~~~~~~~~~~~

# Read GeoJSON file
aoi = json.load(open(aoi_path))

# Get geometry for our AOI
aoi_geom = None
for area in aoi['features']:
    if area['properties']['name'] == aoi_name:
        aoi_geom = area['geometry']
aoi_coords = aoi_geom['coordinates'][0][0]
aoi_x = [i for i,j in aoi_coords]
aoi_y = [j for i,j in aoi_coords]

# Get centroid
centroid = (sum(aoi_x) / len(aoi_coords), sum(aoi_y) / len(aoi_coords))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# STEP 3: MAKE API REQUEST TO PLANET
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Set request parameters
endpoint_request = {
    "item_types": ['PSScene4Band'],
    "filter": {
        "type": "AndFilter",
        "config": [
            {
                "type": "GeometryFilter",
                "field_name": "geometry",
                "config": aoi_geom
            },
            {
                "type": "DateRangeFilter",
                "field_name": "acquired",
                "config": {
                    "gte": lastWeek.isoformat() + 'Z',
                    "lte": today.isoformat() + 'Z'
                }
            }
        ]
    }
}

# Execute request
resp = requests.post(api_address, auth=requests.auth.HTTPBasicAuth(api_key, ''), json=endpoint_request)

# Inspect result
resp.json()["features"][0]

# ~~~~~~~~~~~~~~~~~~~~
# STEP 4: PLOT RESULTS
# ~~~~~~~~~~~~~~~~~~~~

# Plot AOI
fig = plt.figure()
ax = fig.gca()
ax.plot(aoi_x,aoi_y, color = "blue")
plt.text(centroid[0], centroid[1], aoi_name, horizontalalignment='center', verticalalignment='center', color = "blue")
#plt.show()

# Plot imagery footprint
for item in resp.json()["features"]:
    coords = item["geometry"]["coordinates"][0]
    x = [i for i, j in coords]
    y = [j for i, j in coords]
    ax.plot(x, y, color = "silver")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# STEP 5: Update PostgreSQL database
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Open connection
conn = psycopg2.connect(decouple.config('DATABASE_URL_PROD'))
cur = conn.cursor()

# Insert new AOI
cur.execute("INSERT INTO img_view_aoi (name, geom, init_lat, init_lon, init_zoom) VALUES(%s, %s, %s, %s, %s) RETURNING id",
            (aoi_name, json.dumps(aoi_geom), centroid[1], centroid[0], 10))

# Link AOI with demo user
new_id = cur.fetchone()[0]
cur.execute("UPDATE img_view_user SET aoi_id = %s WHERE username = 'bcit_demo'", [new_id])

# Commit changes and close connection
conn.commit()
cur.close()
conn.close()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# STEP 6 & 7: View imagery on Django/Leaflet web app
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

webbrowser.open('http://ec2-35-86-122-148.us-west-2.compute.amazonaws.com/', new=2)

