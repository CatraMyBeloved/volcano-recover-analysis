# Main concepts

## NDVI (Normalized difference vegetation index)

### Definition

NDVI
: Metric to quantify density of vegetation in a specific area. Calculated from spectrometric data, often gathered by satellites.

### Calculation

NDVI is calculated using two specific bands from spectrometric data, red and near-infrared. It utilizes the fact that plants absorb red and reflect near-infrared light. The ratio of reflected light for both of these is used in the following formula to create the NDVI.

$NDVI = \frac{NIR - Red}{NIR + Red}$

### Interpretation

Since NDVI uses ratios of reflected light, the result of the formula is always a decimal between -1 and 1. Values close to -1 often represent water, clouds or snow fields. Low values close to 0 represent bare soil, with higher values(higher than 0.2) representing higher density of vegetation. Values of 0.6 or above are generally considered to indicate dense canopies.

### Limitations

NDVI is vulnerable to interference from atmospheric composition, cloud coverage and soil wetness.

## Ecological succession

### Definition

Ecological succession
: Ecological succession is the process of change in the species that make up an ecological community over time. 

### Process

Ecological succession can be grouped into two general phases.

#### Primary succession

Primary succession takes place when newly available area is colonized. This might occur with newly exposed rock, lava flows or newly exposed glacial tills. Microorganisms as well as lichens and moss begin breaking down the exposed rock into initial soil. Small, grassy plants begin establishing themselves, and as the soil develops larger, brushy plants follow. Animals begin returning to the area, symbolizing the slow first steps of a functioning ecosystem. This process can take centuries to unfold.

#### Secondary succession

Secondary succession takes place when a disturbance removes the previous ecosystem, but leaves remnants behind. Beginning from bare soil, grassy and bushy plants begin growing back. Small trees begin to develop, followed by the first fast-growing larger pieces of vegetation. Over time, large canopies develop and the ecosystem returns to similar state as before the disturbance. Typical disturbances might include fires, floods or in our case ash fall.

###  Relevancy

Our analysis will largely focus on secondary succession, since primary succesion takes place over a time frame that our data does not cover. Especially the edges where both types meet (lava flows) will be analysed.

## Remote sensing

### Definition

Remote sensing
: emote sensing is the acquisition of information about an object or phenomenon without making physical contact with the object, in contrast to in situ or on-site observation. The term is applied especially to acquiring information about Earth and other planets.

### Passive sensing

Passive sensing includes all data collected by passive sensors. This is the kind that our project uses the most. Typical techniques include photography and infrared.

### Active sensing

Active sensing includes all data collected by sensor that use emitted energy to collect data. Examples include LiDAR or RADAR. 

### Spectral bands

The data used in this project is captured by satellites which capture multiple frequency bands. Each band responds to a different frequency of electromagnetic waves collected. Most relevant for this project are red and near-infrared light.

### Resolution

Resolution, when talking about satellite data, is determined by two factors. Spatial resolution represents the level of image detail. Most of the time, it is given as meter / pixel. Temporal resolution represents the time that passes between two fly-bys. It can be considered similar to framerate. Lastly, spectral resolution represents the amount of different wavelength bands collected.

### Possible interferences

Since the collected radiation has to travel through the atmosphere, it is prone to atmospheric interference. Atmospheric composition, clouds and other factors can influence measurements and need to be accounted for.

## Volcanic deposit types: Lava flow

### Definition

Lava flow
: A lava flow is an outpouring of lava during an effusive eruption.

### Relevancy

Lava flows often occur during effusive eruptions. During these, a steady flow of lava flows out of a volcano onto the ground. Due to their relatively low viscosity, certain types of lava can flow for kilometres before solidifying. Lava flows completely destroy the soil and vegetation in their way, leaving behind newly formed rock. These are candidates for primary succession.

## Volcanic deposit types: Volcanic ash

### Definition

Volcanic ash
: Volcanic ash consists of fragments of rock, mineral crystals, and volcanic glass, produced during volcanic eruptions and measuring less than 2 mm (0.079 inches) in diameter.

### Relevancy

Volcanic ash is often produced during more explosive parts of eruptions, and can travel long distances in the atmosphere. Different thicknesses of ash-fall can result in different effects on the environment, with thicker falls resulting in destroyed vegetation. Since the soil is not destroyed, and in many cases even fertilized, these are prime candidates for secondary succession. 

## Volcanic deposit types: Pyroclastic flow

### Definition

Pyroclastic flow
: A pyroclastic flow (also known as a pyroclastic density current or a pyroclastic cloud)[1] is a fast-moving current of hot gas and volcanic matter (collectively known as tephra) that flows along the ground away from a volcano at average speeds of 100 km/h (30 m/s; 60 mph) but is capable of reaching speeds up to 700 km/h (190 m/s; 430 mph).

### Relevancy

Pyroclastic flows are the most destructive volcanic deposits. Vegetation in their path is completely destroyed, and soil sterilized due to high temperatures. Potential candidate for primary succession.

## Vegetation recovery patterns

### Definition

Recovery patterns
: Patterns that commonly occur in vegetation recovery. Dependent on local factors such as soil and seed banks.

### Relevancy

Since this project focuses on satellite data, alot of the common patterns will remain difficult to detect. The general pattern follows the same as succession. Smaller plants prepare the soil, and are slowly followed by larger and larger plants. 

## Border development

### Definition
 
Border developments
: Developments on the edges of typically primary succession areas such as lava flows.

### Relevancy

One of this projects focuses will be on the development of vegetation on the borders of lava flows. We hope to capture the different stages of primary succession depending on distance to the border.