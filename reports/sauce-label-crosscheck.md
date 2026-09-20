# 標籤判讀 × OFF 成分文字 交叉驗證

判讀 387 筆　對得到獨立成分文字的 350 筆　**沒有參照可比的 37 筆**

比的是**詞的回收率與精確率**，不是字串相等：
回收率低＝我們漏讀；精確率低＝我們多讀了不該有的（多半是營養標示混進來）。

**沒有參照可比的那幾筆完全沒有被驗過**，而它們在總表上跟驗過的長得一模一樣。

## 可疑的 50 筆（回收率 < 50% 或 精確率 < 50%）

### Jalapeno hot sauce

回收率 0.0　精確率 0.0

- 漏讀：bug, dietary, img, omcg, omg, per, tsp, unissoo
- 多讀：acid, benzoate, citric, flavor, following, garlic, gum, jalapeno, lactate, onion, peppers, salt

```
我們讀到： INGREDIENTS: VINEGAR, WATER, JALAPENO PEPPERS, ONION, GARLIC, SALT, NATURAL FLAVOR, XANTHAN GUM, CALCIUM LACTATE, CITRIC ACID, POTASSIUM SORBATE, AND LESS THAN 2% OF EACH OF THE FOLLOWING: SPICE, SUGAR, AND SODIUM BENZOATE.
OFF 的文字： 1 tsp (5g) serving size amount per serving calories % daily value total fat 1g saturated fat og %0 trans fat og cholesterol omg %0 sodium 45mg 2% total carbohydrate og %0 dietary fiber og total sugars og 0% includes og added sugars protein og vitamin d omcg 0% calcium img 0% iron omg %0% 0% bug unis
```

### Pepper sauce

回收率 0.071　精確率 0.062

- 漏讀：acid, ascorbic, chloride, citric, distilled, fire, garlic, gum, roasted, salt, vinegar, water
- 多讀：acide, ail, ascorbique, chlorure, citrique, distill, eau, gomme, grill, piments, poudre, sel

```
我們讀到： Piments Jalapenos grillés, eau, vinaigre distillé, ail en poudre, sucre, acide ascorbique, acide citrique, sel, gomme de xanthane, chlorure de calcium.
OFF 的文字： Fire roasted jalapenos, water, distilled vinegar, garlic powder, sugar, salt, ascorbic acid, citric acid, xanthan gum. calcium chloride
```

### Cholula Salsa Picante

回收率 0.077　精確率 0.111

- 漏讀：agua, blanco, chiles, cido, especias, goma, manzana, piqu, sal, tico, vinagre, xantana
- 多讀：gum, peppers, piquin, salt, spices, vinegar, water, xanthan

```
我們讀到： INGREDIENTS: WATER, PEPPERS (ARBOL AND PIQUIN), SALT, VINEGAR, SPICES AND XANTHAN GUM.
OFF 的文字： Agua, 5% chiles (arbol y piquín), sal, vinagre blanco (agua y ácido acético), vinagre de manzana (agua y ácido acético), especias y goma xantana.
```

### La Victoria Red Chile Sauce

回收率 0.086　精確率 0.143

- 漏讀：aceite, agua, ajo, alimenticio, almid, asa, calcio, cido, cloruro, deshidratadas, destilado, diario
- 多讀：acid, chloride, dehydrated, distilled, food, fumaric, garlic, gluten-free, modified, oil, pods, red

```
我們讀到： INGREDIENTS: WATER, RED CHILES, DEHYDRATED CALIFORNIA CHILE PODS, DISTILLED VINEGAR, SALT, MODIFIED FOOD STARCH, SOYBEAN OIL, SPICES, GARLIC POWDER, CALCIUM CHLORIDE AND FUMARIC ACID. GLUTEN-FREE.
OFF 的文字： AGUA, CHILES ROJOS, VAINAS DE CHILE DE CALIFORNIA DESHIDRATADAS, VINAGRE DESTILADO, SAL, ALMIDÓN ALIMENTICIO MODIFICADO, ACEITE DE SOYA, 0% ESPECIAS, POLVO DE AJO, CLORURO DE CALCIO Y ÁCIDO FUMÁRICO, 0% whethe, asa: 5 sauces, %Valor Diario* or salsa kitchen your sec with us, Omg 0% 439 13% valagtica
```

### hot sauce

回收率 0.098　精確率 0.444

- 漏讀：apeppershs, baking, bre, buifits, call, camp, cay, com, comments, dot, everything, fants
- 多讀：central, dip, vinegar, water, wings

```
我們讀到： INGREDIENTS: VINEGAR, WATER, FRANK'S REDHOT BUFFALO WINGS CENTRAL IN BUFFALO, N.Y. INGREDIENTS: VINEGAR, WATER, FRANK'S REDHOT BUFFALO WINGS CENTRAL IN BUFFALO, N.Y. FRANK'S REDHOT BUFFALO CHICKEN DIP
OFF 的文字： inesan frank's redhot original, mu n apeppershs be வீபூர் for over 90 years. the great taste of fants reht ingredient used is the original buifits winsceted in m frank's redhot buffalo chicken d gk se 1/2 cay kids grimal kancing 1/2 pranks redot opal camp in : |-quant baking dot. bre 399 for 20 mm u
```

### Sriracha Hot Chili Sauce

回收率 0.1　精確率 0.1

- 漏讀：chilis, essigs, kaliumsorbat, knoblauch, konservierungsmittel, natriumbisulfit, salz, ure, zucker
- 多讀：acetic, acid, bisulfite, chili, garlic, gum, preservatives, salt, sorbate

```
我們讀到： INGREDIENTS: CHILI, SUGAR, SALT, GARLIC, ACETIC ACID, POTASSIUM SORBATE AND SODIUM BISULFITE AS PRESERVATIVES, XANTHAN GUM.
OFF 的文字： Chilis, Zucker, Knoblauch, Salz, Essigsäure E260, Konservierungsmittel Kaliumsorbat E202, Konservierungsmittel Natriumbisulfit E222, Xanthan E415.
```

### Sambal Oelek

回收率 0.111　精確率 0.2

- 漏讀：branntweinessig, johannisbrotkernmehl, meersalz, paprika, quot, verdickungsmittel, wasser, zitronensaftkonzentrat
- 多讀：garlic, pepper, salt, vinegar

```
我們讀到： INGREDIENTS: CHILI PEPPER, GARLIC, SALT, VINEGAR
OFF 的文字： Paprika, Wasser, Chili, Branntweinessig&quot;, Meersalz, Zitronensaftkonzentrat, Verdickungsmittel: Johannisbrotkernmehl
```

### Organic sriracha chili sauce

回收率 0.111　精確率 0.333

- 漏讀：acetic, acid, garlic, gum, metabisulfite, salt, sorbate, xanthan
- 多讀：sauce, sriracha

```
我們讀到： ORGANIC SRIRACHA CHILI SAUCE
OFF 的文字： Chili, Sugar, Salt, Garlic, Acetic Acid, Potassium Sorbate, Sodium Metabisulfite, Xanthan Gum
```

### Master, Fermented Chili Bean Sauce

回收率 0.125　精確率 0.167

- 漏讀：chili, l-glutamate, monosodium, oil, salt, soybeans, water
- 多讀：eau, huile, piment, soja, sucre

```
我們讀到： INGREDIENTS :PIMENT 37%,SOJA 37%,SUCRE,EAU,HUILE DE SESAME
OFF 的文字： Soybeans, chili, salt,water, sesame oil, monosodium l-glutamate
```

### chili sauce

回收率 0.163　精確率 0.667

- 漏讀：according, am-, are, ase, based, calculated, call, caloriediet, card, chil, chilipepper, comments
- 多讀：chili, corn, modified, paste

```
我們讀到： INGREDIENTS: SUGAR, WATER, VINEGAR, CHILI PEPPER, TOMATO PUREE (WATER, TOMATO PASTE), MODIFIED CORN STARCH, SALT, CHILI POWDER, GARLIC POWDER, GINGER.
OFF 的文字： values are odsed ona 2,000 calorie diet, edents sugar nater, vinegar, chilipepper, tomatopuree (nater tomat requirements percentage calculated based on 2,000 hot card recipes. ase mofed corm starch, salt, chil powder garlicponder ginger values are vased ona 2,000 caloriediet percentage to be counted
```

### Sweet Chili Sauce

回收率 0.174　精確率 0.211

- 漏讀：box, brands, call, canada, cap, chicago, com, conagra, discard, empty, glass, oney
- 多讀：canola, corn, flavor, garlic, ginger, honey, modified, oil, onion, peppers, salt, starch

```
我們讀到： INGREDIENTS: WATER, SUGAR, HONEY, CHILI PASTE (RED CHILI PEPPERS, GARLIC, ONION, SALT, WATER), SALT, MODIFIED CORN STARCH, WHITE WINE, VINEGAR, SALT, WHITE WINE, GINGER, SALT, CANOLA OIL, NATURAL FLAVOR.
OFF 的文字： water, sugar, oney, chili paste (red chili peper contains: soy, wheat. conagra brands p.o.box 3534 chicago, il 60654 or call 1-800-298-0 smartlabe product of canada ww.pfchangshomemenu.com w call 1-800-298-47720. discard seal, empty & replace cap glass
```

### Hot chilli sauce

回收率 0.25　精確率 0.111

- 漏讀：msg, pepper, tomatoes
- 多讀：chilli, cumin, gum, onion, salt, tomato, vineger, xanthan

```
我們讀到： INGREDIENTS: TOMATO, ONION, GARLIC, CHILLI, SUGAR, SALT, VINEGER, XANTHAN GUM, CUMIN.
OFF 的文字： Pepper, Tomatoes, sugar, garlic, msg
```

### Chipotle Bitchin' Sauce

回收率 0.25　精確率 0.056

- 漏讀：bitchin, chipotle, vegan
- 多讀：almonds, chipotles, garlic, grapes, lemon, nuts, oil, roasted, salt, sea, soy, soybeans

```
我們讀到： INGREDIENTS: WATER, GRAPES, OIL, ALMONDS, LEMON JUICE, SOY SAUCE (WATER, SOYBEANS, ROASTED SOYBEANS, SALT), NATURAL YEAST, CHIPOTLES (CHIPOTLES, TOMATO, SUGAR, GARLIC, SPICES), SEA SALT, CONTAINS: ALMONDS (TREE NUTS).
OFF 的文字： CHIPOTLE BITCHIN VEGAN SAUCE
```

### Avocado Hot Sauce - Original

回收率 0.25　精確率 0.714

- 漏讀：black, coriander, cornflour, flavouring, garlic, green, lemon, onion, parsley, pepper, roasted, salt
- 多讀：made, sauce

```
我們讀到： A sauce made with mango, avocado, jalapeno & habanero chilli
OFF 的文字： Mango Puree (22%), Vinegar, Avocado (14%), Onion Puree, Green Pepper Puree, Water, Roasted Jalapeno Puree (6%), Parsley, Salt, Coriander, Garlic Puree, Lemon Juice, Cornflour, Habanero Chilli, Ground Black Pepper, Natural Spinach Flavouring
```

### lime chili sauce

回收率 0.278　精確率 0.167

- 漏讀：dietary, efrigerate, food, how, igredients, much, not, noush, significant, source, tells, tozal
- 多讀：acetic, acid, chile, chipotle, cilantro, corn, distilled, flavor, garlic, green, gum, jalapeno

```
我們讀到： INGREDIENTS: WATER, CANOLA OR SOYBEAN OIL, CANE SUGAR, JALAPENO GREEN CHILE PEPPERS (JALAPENO PEPPERS, SALT, ACETIC ACID), DISTILLED VINEGAR, LIME JUICE CONCENTRATE, SPICES, GARLIC, SEA SALT, CORN STARCH, ONIONS, CILANTRO, SUNFLOWER LECITHIN, NATURAL FLAVOR, XANTHAN GUM, CHIPOTLE PEPPER POWDER, VITA
OFF 的文字： 1% tozal sugars 2g includes 1g added sugars 2% not a significant source of cholesterol, dietary fiber vitamin d, calcium, iron and potassium. * the % daily value tells you how much a nutrient in a serving of food contributes to a daily diet. 2,000 calories a day is used for general nutrition advice.
```

### Inca's food, aji panca paste

回收率 0.286　精確率 0.154

- 漏讀：acid, benzoate, citric, panca, preservative
- 多讀：cilantro, cumin, garlic, gum, lime, onion, poblano, serrano, tomatillo, tomato, xanthan

```
我們讀到： INGREDIENTS: TOMATO, TOMATILLO, ONION, CILANTRO, POBLANO PEPPER, SALT, SERRANO PEPPER, GARLIC, ONION, LIME JUICE CONCENTRATE, XANTHAN GUM, CUMIN.
OFF 的文字： Panca pepper, salt, citric acid and sodium benzoate as preservative.
```

### Chili Garlic Sauce

回收率 0.286　精確率 0.364

- 漏讀：acetic, acid, corn, dehydrated, modified, peppers, rice, salted, starch, water
- 多讀：disodium, edta, flavor, gum, pepper, sorbate, xanthan

```
我們讀到： INGREDIENTS: VINEGAR, GARLIC, CHILI PEPPER, SALT, SUGAR, XANTHAN GUM, POTASSIUM SORBATE, CALCIUM DISODIUM EDTA, NATURAL FLAVOR.
OFF 的文字： salted chili peppers (chili peppers, salt), water, sugar, rice vinegar, dehydrated garlic, modified corn starch, acetic acid.
```

### Creamy garlic red pepper hot sauce

回收率 0.3　精確率 0.667

- 漏讀：acid, bell, canola, citric, cumin, distilled, guar, jalapenos, non-gmo, oil, paste, peppers
- 多讀：flavor, pepper, xanthan

```
我們讀到： INGREDIENTS: WATER, VINEGAR, GARLIC, RED PEPPER, SALT, XANTHAN GUM, NATURAL FLAVOR.
OFF 的文字： Water, red jalapenos, non-gmo canola oil, red bell peppers, tomato paste, distilled white vinegar, salt, garlic, cumin, citric acid, and guar gum.
```

### Cravin cajun hot sauce

回收率 0.308　精確率 0.222

- 漏讀：alginate, distilled, guar, gums, louisiana, peppers, red, selected, yellow
- 多讀：acid, annatto, benzoate, citric, color, flavor, garlic, gum, lactate, onion, pepper, sorbate

```
我們讀到： INGREDIENTS: VINEGAR, WATER, TOMATO PUREE, SUGAR, SALT, GARLIC, ONION, CAYENNE PEPPER, NATURAL FLAVOR, XANTHAN GUM, CALCIUM LACTATE, POTASSIUM SORBATE, SODIUM BENZOATE, CITRIC ACID, ANNATTO COLOR.
OFF 的文字： Selected louisiana cayenne peppers, distilled vinegar, salt, guar, sodium alginate, xanthan gums, yellow no. 6 and red no. 40.
```

### Mexico Lindo, Green Habanero Hot Sauce, Extra Hot

回收率 0.333　精確率 0.455

- 漏讀：acid, antioxidant, benzonate, blue, citric, metabisulfate, preservative, spices, sulfites, yellow
- 多讀：cilantro, flavor, garlic, green, salt, vinegar

```
我們讀到： INGREDIENTS: WATER, VINEGAR, SALT, SUGAR, GREEN HABANERO PEPPER, GARLIC, CILANTRO, XANTHAN GUM, NATURAL FLAVOR.
OFF 的文字： Water,habanero pepper puree, sodium benzonate (preservative), sodium metabisulfate (antioxidant) ,xanthan gum,spices,citric acid,FD&C (Yellow No.5 & Blue No. 1). Contains Sulfites & Yellow No.5).
```

### Fermented Chili Paste (Doubanjiang)

回收率 0.357　精確率 0.312

- 漏讀：additives, beans, broad, flour, food, rapeseed, red, spice, wheat
- 多讀：acid, brine, citric, disodium, fermented, garlic, guanylate, inosinate, pepper, soybean, spices

```
我們讀到： CHILI PEPPER, SALT, SUGAR, SOYBEAN OIL, GARLIC, FERMENTED SOYBEAN BRINE, SPICES, SODIUM BENZOATE, POTASSIUM SORBATE, CITRIC ACID, DISODIUM INOSINATE, DISODIUM GUANYLATE.
OFF 的文字： Red chili, Broad beans, Salt, Wheat flour, Rapeseed oil, Spice, Food additives(Potassium sorbate, Sodium benzoate)
```

### Squeeze Presser Creamy Buffalo Sauce

回收率 0.373　精確率 1.0

- 漏讀：ail, all, amidon, arrel, call, canada, d'ail, dients, eau, gomme, her, huile
- 多讀：—

```
我們讀到： Hot sauce (aged cayenne red peppers, vinegar, water, salt, garlic powder), Water, Soybean oil, Sugar, Modified corn starch, Dehydrated garlic, Xanthan gum, Natural flavour.
OFF 的文字： hot sauce (aged cayenne red peppers, vinegar, water, salt, garlic powder), water, soybean oil, sugar, modified corn starch, dehydrated garlic, xanthan gum, natural flavour. %vq* ingrédients: sauce piquante (piments de cayenne rouges vieillis, vinaigre, eau, sel, poudre d'ail), eau, huile de fève de 
```

### Jalapeno hot sauce imp

回收率 0.375　精確率 0.25

- 漏讀：gum, mash, pepper, water, xanthan
- 多讀：chile, frais, fresco, peppers, pimentos, sal, sel, vinagre, vinaigre

```
我們讀到： INGREDIENTS: Pimentos jalapeno frais, vinaigre et sel. INGREDIENTS: Fresh jalapeno chile peppers, vinegar and salt. INGREDIENTS: Chile jalapeno fresco, vinagre y sal.
OFF 的文字： Jalapeno pepper mash (water, jalapeno pepper), vinegar, salt, xanthan gum.
```

### Golden Sriracha

回收率 0.382　精確率 0.448

- 漏讀：bell, canola, corn, cream, cultured, flavors, garlic, glutamate, malic, molasses, monosodium, onion
- 多讀：annatto, benzoate, cheddar, cheese, culture, enhancers, enzymes, flavor, lactic, lecithin, pepper, preservatives

```
我們讀到： INGREDIENTS: VEGETABLE OIL, CHEDDAR CHEESE (MILK, CHEESE CULTURE, SALT, ENZYMES), TOMATO POWDER, SRIRACHA PEPPER, SALT, MALTODEXTRIN, NATURAL FLAVOR, CITRIC ACID, ANNATTO (COLOR), PAPRIKA, SUGAR, SPICES, LACTIC ACID, SOY LECITHIN, SODIUM BENZOATE AND POTASSIUM SORBATE (PRESERVATIVES), DISODIUM INOSI
OFF 的文字： corn, vegetable oil (corn, canola, soybean, and/or sunflower oil), corn maltodextrin, sugar, natural flavors, artificial flavors, salt, garlic powder, monosodium glutamate, onion powder, citric acid, whey, spices, paprika, yeast extract, potassium salt, red bell peppers, sour cream (cultured cream, 
```

### CHILI CRISP

回收率 0.39　精確率 1.0

- 漏讀：ail, arachides, chalote, contenir, contient, dients, eau, foods, huile, ingr, leigh, ltd
- 多讀：—

```
我們讀到： INGREDIENTS: Soybean oil, Dried red chili, Shallot, Sugars (sugar, tamarind paste (tamarind, water)), Garlic, Salt, Tocopherol. Contains: Soy. May Contain: Peanuts, Tree nuts.
OFF 的文字： Soybean oil, Dried red chili, Shallot, Sugars (sugar, tamarind paste (tamarind, water)), Garlic, Salt, Tocopherol. Contains: Soy. May Contain: Peanuts, Tree nuts.  Ingrédients : Huile de soya, Piment rouge séché, Échalote, Sucres (sucre, pâte de tamarin (tamarin, eau)), Ail, Sel. Tocopherol. Contien
```

### Franks Red Hot Original cayenne pepper sauce

回收率 0.421　精確率 0.889

- 漏讀：any, bake, cistilled, combine, food, fran, mata, per, thi, tsp, utrition
- 多讀：distilled

```
我們讀到： INGREDIENTS: AGED CAYENNE RED PEPPERS, DISTILLED VINEGAR, WATER, SALT AND GARLIC POWDER.
OFF 的文字： utrition facts about 71 servings per container serving size 1 tsp. (5ml) calories per serving amount/serving total fat og sodium 190mg total carb. og protein og 4455 e mata 0 ingredients aged cayenne red peppers, cistilled vinegar, water salt and garlic powder any llc % dv 3-9416 0% 8% 0% p fran com
```

### Green Chili Salsa Mild

回收率 0.429　精確率 1.0

- 漏讀：ave, college, collins, com, compromise, don't, eat, family, fine, fort, gmo, more
- 多讀：—

```
我們讀到： INGREDIENTS: TOMATOES (VINE-RIPENED FRESH TOMATOES, TOMATO JUICE, SALT, CALCIUM CHLORIDE AND CITRIC ACID), GREEN CHILES (GREEN CHILI PEPPERS, SALT, CITRIC ACID), ONIONS, WATER, SEA SALT, CILANTRO, COARSE CHILES, GARLIC, CITRIC ACID AND SPICES
OFF 的文字： no added sugars or preservatives non-gmo family owned since 1988 @ don't compromise, eat roberto's! ingredients: tomatoes (vine-ripened fresh tomatoes, tomato juice, salt, calcium chloride and citric acid), green chiles (green chili peppers, salt, citric acid), onions, water, sea salt, cilantro, coa
```

### Chili Garlic Sauce

回收率 0.429　精確率 1.0

- 漏讀：acetic, acid, chili, corn, dehydrated, modified, rice, salted
- 多讀：—

```
我們讀到： INGREDIENTS: PEPPERS, SALT, WATER, VINEGAR, GARLIC, STARCH.
OFF 的文字： salted chili peppers (chili peppers, salt), water, sugar, rice vinegar, dehydrated garlic, modified corn starch, acetic acid.
```

### Matouk's, Hot Pepper Sauce, Salsa Picante

回收率 0.435　精確率 0.526

- 漏讀：colour, corn, modified, mustard, oil, preservative, sorbate, soybean, spices, starch, vinegar, water
- 多讀：cilantro, cumin, garlic, lime, poblano, roasted, serrano, tomatillo, tomato

```
我們讀到： INGREDIENTS: AGED PICKLED SCOTCH BONNET PEPPERS, ROASTED GARLIC, ROASTED ONION, ROASTED TOMATO, ROASTED TOMATILLO, ROASTED CILANTRO, ROASTED POBLANO PEPPER, SALT, ROASTED SERRANO PEPPER, DRIED GARLIC, DRIED ONION, LIME JUICE CONCENTRATE, XANTHAN GUM, CUMIN.
OFF 的文字： Aged pickled scotch bonnet peppers (pepper, vinegar, salt), water, vinegar, modified corn starch, salt, mustard, onion powder, spices, potassium sorbate (as a preservative), soybean oil, xanthan gum, colour (fd & c yellow no.5)
```

### Chili sauce for burgers and dogs

回收率 0.441　精確率 0.714

- 漏讀：ating, carbcnydrate, elled, how, ides, lecithin, lor, moked, much, mutrient, ngredients, oil
- 多讀：black, cayenne, color, distilled, pepper, smoked

```
我們讀到： INGREDIENTS: WATER, SOY GRITS, TOMATO PASTE, LESS THAN 2% CHILI POWDER, BEEF SUGAR, SALT, BROWN SUGAR, WHITE DISTILLED WHITE VINEGAR AND FILTERED WATER, SMOKED PAPRIKA, ONION POWDER, GARLIC POWDER, CAYENNE PEPPER, BLACK COLOR, CAYENNE PEPPER, CONTAINS: SOY
OFF 的文字： tdium total carbcnydrate s ating2% ras vitamin d, calcium, iron and potassium, ay vaue dv tells you how much a mutrient in a w d contributes to a daily diet, 2,000 calories a sed lor general nutrition advice, ngredients water, soy grits, tomato paste ides) less than 2% chili powder, beef l s ar salt
```

### gochujang

回收率 0.45　精確率 0.783

- 漏讀：anutrient, buyer, cerritos, com, dextrin, dietary, fax, food, how, korea, lcohol, malto
- 多讀：chili, gochujang, korean, maltodextrin, paste

```
我們讀到： Gochujang, Korean Chili Paste (Allergy Alert: Contains Soy, Wheat) Ingredients: Rice, Water, Corn syrup, Red pepper powder, Salt, Soybean, Alcohol, Wheat extract, Soy seasoning(Soybean, Wheat gluten, Salt, Alcohol, Yeast extract, Maltodextrin), Garlic concentrate, Koji-starter
OFF 的文字： rice, water, corn syrup, red amount per serving pepper powder, salt, soybean, álcohol, wheat extract, soy seasoning(soybean, wheat gluten, salt, alcohol, yeast extract, total fat og malto dextrin), garlic concentrate, koji-starter (allergy alert: contains soy, wheat) 40 %daily value calories 0% 0% s
```

### la michoacana mangohelada mango y chamoy

回收率 0.452　精確率 0.7

- 漏讀：canula, cay, chi, cuar, equipment, frozen-, gluten-frlodonuced, milk, nne, nuts, potassi, shared
- 多讀：canola, caramel, cayenne, chili, guar, oil

```
我們讀到： INGREDIENTS: WATER, CANE SUGAR, MANGOES, SALT, CITRIC ACID, PAPRIKA, CHILI PEPPER, GUAR GUM, FD&C YELLOW #5 AND #6, NATURAL AND ARTIFICIAL FLAVORS, FD&C RED #40, CAYENNE PEPPER, CARAMEL COLOR, POTASSIUM SORBATE, CANOLA OIL.
OFF 的文字： water, cane sugar, mangoes, salt, citric acid, paprika, chi pepper, cuar gum, fd,c yellow #5 and #6, natural and artificial flavors, fd,c red #40, cay nne pepper, uaramel color, potassiùm sorbate, canula uil, 877-689-3740 keep frozen-10°f gluten-frlodonuced on shared equipment with soy, wheat, tree 
```

### Coney Island chili sauce

回收率 0.466　精確率 1.0

- 漏讀：all, approximate, are, austin, based, can, car, careful, com, deded, depending, dietary
- 多讀：—

```
我們讀到： INGREDIENTS: BEEF AND PORK, WATER, ONIONS, TOMATO PASTE, TEXTURED SOY FLOUR, CONTAINS 2% OR LESS OF MODIFIED FOOD STARCH, OATMEAL, CHILI POWDER (CHILI PEPPERS, FLAVORING), CORN FLOUR, SUGAR, CONCENTRATED ROCHESTER SAUCE (DISTILLED VINEGAR, CORN SYRUP, WATER, SALT, GARLIC POWDER, SPICES INCLUDING CEL
OFF 的文字： total car dietary fiber og sugars 2g protein 3g 5% serving. careful. let 0% chili stand in microwave 1 minute and stir before vitamin a 2% vitamin c 0% vary. times given are all microwaves and stoves calcium 0% . iron 2% www.hormel.com percent daily values are based on a 2,000 calorie diet. your dai
```

### Thai style green chili sauce

回收率 0.471　精確率 0.762

- 漏讀：acidfey, caesga, che, cirka, geen, jalapeno, kofer, lenes, lime, lme, octe, peppers
- 多讀：acidified, cultured, dextrose, flavor, potato

```
我們讀到： INGREDIENTS: GREEN CHILI PEPPER, RICE BRAN OIL, GARLIC PUREE (GARLIC, CITRIC ACID [ACIDIFIED TO 2% OR LESS OF SALT, LEMON GRASS PUREE (LEMON GRASS, WATER, XANTHAN GUM, CITRIC ACID, NATURAL FLAVOR, POTATO EXTRACT, MALTODEXTRIN, CULTURED DEXTROSE.)
OFF 的文字： KOFER) LME JUICE POWDER (MALTODEXTRIN, LIME JUICE SOLIDS), GROUND THAI LIME LENES CHE OCTE GEEN JALAPENO PEPPERS (ROASTED GREEN JALAPENO PEPPERS, VINEGAR) SHALLO, CAESGA CONTAINS 24 OR LESS OF SALT, LEMON GRASS PUREE (LEMON GRASS, WATER, XANTHAN GUM, CIRKA TIARDENTS GREEN CHILI PEPPER, RICE BRAN OIL
```

### HOT HONEY HAM

回收率 0.472　精確率 0.962

- 漏讀：call, color, comments, cst, date, days, designe, free, frost, gluten, how, itw
- 多讀：paprika

```
我們讀到： INGREDIENTS: HAM CURED WITH WATER, HONEY, SALT, LESS THAN 2% OF SUGAR, MODIFIED CORN STARCH, VINEGAR, SODIUM PHOSPHATES, MALTODEXTRIN, AUTOLYZED YEAST, DEXTROSE, NATURAL FLAVOR, BROWN SUGAR, SODIUM ERYTHORBATE, SODIUM NITRITE. COATED WITH: DRIED HONEY, RED PEPPER, NATURAL SMOKE FLAVOR, NATURAL FLAVO
OFF 的文字： HAM CURED WITH WATER 60 HONEY, SALT, LESS THAN 2% OF SUGAR, MODIFIED % Daily Value 3% 3% CORN STARCH, VINEGAR, SODIUM PHOSPHATES, MALTODEXTRIN, AUTOLYZED YEAST, DEXTROSE, NATURAL FLAVOR, BROWN SUGAR, SODIUM ERYTHORBATE, SODIUM NITRITE COATED WITH: DRIED HONEY, RED PEPPER, NATURAL SMOKE FLAVOR, NATUR
```

### Tahini Whole Seed Harissa

回收率 0.5　精確率 0.214

- 漏讀：flavors, harissa, roasted
- 多讀：black, cayenne, coriander, cumin, flakes, garlic, lemon, paprika, pepper, red, water

```
我們讀到： INGREDIENTS: SESAME SEEDS, WATER, SALT, GARLIC, LEMON JUICE, RED PEPPER FLAKES, PAPRIKA, CUMIN, CORIANDER, CAYENNE PEPPER, BLACK PEPPER.
OFF 的文字： roasted whole sesame seeds natural flavors (harissa), salt,
```

### Louisiana sauce hot

回收率 0.5　精確率 0.1

- 漏讀：aged, peppers
- 多讀：acid, cayenne, citric, disodium, edta, flavor, garlic, gum, lactate, onion, paprika, pepper

```
我們讀到： INGREDIENTS: TOMATO PUREE (CITRIC ACID, CALCIUM LACTATE), WATER, VINEGAR, SALT, SUGAR, GARLIC, ONION, NATURAL FLAVOR, SPICES, XANTHAN GUM, CALCIUM DISODIUM EDTA (PRESERVATIVE), RED PEPPER, PAPRIKA, CAYENNE PEPPER.
OFF 的文字： Aged peppers, vinegar, salt.
```

### Hot Honey

回收率 0.5　精確率 0.1

- 漏讀：jalapeno
- 多讀：chili, flavor, garlic, gum, lemon, pepper, red, salt, xanthan

```
我們讀到： INGREDIENTS: HONEY, RED CHILI PEPPER, SUGAR, GARLIC, LEMON JUICE CONCENTRATE, XANTHAN GUM, SALT, NATURAL FLAVOR.
OFF 的文字： honey, jalapeno extract
```

### Born in Buffalo Wing Sauce

回收率 0.5　精確率 0.444

- 漏讀：butter, oil, sauce, soybean
- 多讀：garlic, onion, salt, tomato, vinegar

```
我們讀到： INGREDIENTS: TOMATO, VINEGAR, SUGAR, SALT, GARLIC, ONION, CAYENNE PEPPER, XANTHAN GUM.
OFF 的文字： Cayenne Pepper Sauce, Butter, Soybean Oil, Xanthan Gum.
```

### Chili sauce

回收率 0.583　精確率 0.35

- 漏讀：chili, flavors, food, gum, xanthan
- 多讀：chilli, corn, dishes, enjoy, fanatics, flavouring, heat, moderate, perfect, sauce, stabiliser, those

```
我們讀到： Chilli Sauce with Garlic - Perfect for those who garlic fanatics who enjoy the moderate heat in dishes. Ingredients: Water, chilli (21%), garlic (21%), sugar, salt, acetic acid, stabiliser: E415, modified corn starch, flavouring.
OFF 的文字： water, chili, garlic, sugar, salt, acetic acid, E415, xanthan gum, modified food starch and natural flavors,
```

### xxx hot pepper sauce

回收率 0.6　精確率 0.429

- 漏讀：choice, onions, peppers, red
- 多讀：acid, citric, gum, mash, onion, pepper, water, xanthan

```
我們讀到： INGREDIENTS: Habanero pepper mash (water, Habanero pepper), carrots, onion, lime juice, vinegar, salt, garlic, citric acid, xanthan gum.
OFF 的文字： Choice red habanero peppers, fresh carrots, onions, lime juice, vinegar, garlic and salt.
```

### Gochuchang

回收率 0.632　精確率 0.414

- 漏讀：agricultural, derived, distilled, fermented, hot, paste, soybean
- 多讀：allergy, cause, concentrated, darken, dextrin, direct, fermentation, further, garlic, gluten, malto, not

```
我們讀到： INGREDIENTS : Rice, Water, Corn syrup, Red pepper powder, Salt, Soybeans, Alcohol, Wheat extract, Soy seasoning(Soybeans, Wheat gluten, Salt, Alcohol, Yeast extract, Malto -dextrin), Concentrated garlic juice, Koji-starter. (Allergy advice : CONTAINS WHEAT & SOYBEANS) · Do not store in direct sunlig
OFF 的文字： Fermented rice paste(rice, salt, koji-starter, water), corn syrup, hot pepper powder, soybean paste(soybean, water, salt, koji-starter), distilled alcohol(derived from agricultural products), salt, wheat extract, fermented soy seasoning(soybean, water, salt, wheat extract, distilled alcohol, yeast e
```

### RedHot Original Cayenne Pepper Sauce

回收率 0.667　精確率 0.316

- 漏讀：aged, distilled, peppers
- 多讀：acid, benzoate, blue, citric, disodium, edta, flavor, gum, pepper, preservative, sorbate, xanthan

```
我們讀到： INGREDIENTS: WATER, SUGAR, VINEGAR, SALT, CAYENNE PEPPER, GARLIC POWDER, NATURAL FLAVOR, XANTHAN GUM, CITRIC ACID, CALCIUM DISODIUM EDTA (PRESERVATIVE), POTASSIUM SORBATE (PRESERVATIVE), SODIUM BENZOATE (PRESERVATIVE), RED 40, YELLOW 6, BLUE 1.
OFF 的文字： Aged cayenne red peppers, distilled vinegar, water, salt, garlic powder
```

### Chili Seasame Oil

回收率 0.75　精確率 0.3

- 漏讀：chillies
- 多讀：black, chilies, garlic, ginger, pepper, salt, seeds

```
我們讀到： SESAME OIL, DRIED RED CHILIES, SESAME SEEDS, GARLIC, GINGER, SALT, BLACK PEPPER, SESAME OIL
OFF 的文字： sesame oil, dried red chillies.
```

### Piri Piri Molho

回收率 0.778　精確率 0.438

- 漏讀：chilli, peppers
- 多讀：acidity, chillies, hot, oil, preservative, regulator, spices, thickener, vegetable

```
我們讀到： INGREDIENTS: Hot chillies (45%), water, salt, vegetable oil, spices, acidity regulator: citric acid, preservative: sodium benzoate and thickener: xanthan gum.
OFF 的文字： chilli peppers (45%), water, salt, citric acid, sodium benzoate, xanthan gum
```

### Hot Sauce, Habanero

回收率 0.818　精確率 0.243

- 漏讀：carrots, spices
- 多讀：acid, aji, ajo, carrot, cebolla, chili, cido, conservante, espesante, fosf, garlic, goma

```
我們讀到： Cane Vinegar, Carrot Pulp, Red Habanero Chili Pepper, Lemon Juice, Salt, Garlic Powder, Onion Powder, Phosphoric Acid, Xanthan Gum (Thickener), Sugar Sodium Benzoate (Preservative). Vinagre de Caña, Pulpa de Zanahoria, Aji Habanero, Jugo de Limón, Sal, Ajo en Polvo, Cebolla en Polvo, Ácido Fosfórico
OFF 的文字： Cane vinegar, habanero pepper, carrots, salt, lemon juice, spices, sugar, xanthan gum, sodium benzoate.
```

### Gia russa, select pasta sauce, hot sicilian

回收率 0.818　精確率 0.209

- 漏讀：imported, plum
- 多讀：all, batches, been, classic, create, enjoy, ensure, expectations, family, favorites, gia, has

```
我們讀到： INGREDIENTS: ITALIAN TOMATOES, ONIONS, OLIVE OIL, SEA SALT, GARLIC, SPICES, BASIL. true & simple Since 1948 Gia Russa's vision has been to create a family of select sauces made from classic Italian recipes using the best produce. We make all our sauces in small batches to ensure the highest level of
OFF 的文字： Imported italian plum tomatoes, onions, olive oil, salt, fresh garlic, spices, basil.
```

### Camouflage Hot Sauce

回收率 0.889　精確率 0.471

- 漏讀：cayenne
- 多讀：aged, base, cream, distilled, hank, milk, salted, sweet, wine

```
我們讀到： INGREDIENTS: HANK BASE (AGED PEPPERS, DISTILLED VINEGAR, SALT, XANTHAN GUM), WINE, GARLIC, SALTED BUTTER (SWEET CREAM, SALT), CILANTRO. CONTAINS MILK.
OFF 的文字： Cayenne peppers, vinegar, garlic, cilantro, butter, salt, xanthan gum
```

### Hot Honey

回收率 1.0　精確率 0.25

- 漏讀：—
- 多讀：feed, infants, microwave, not, one, this, under, warning, year

```
我們讀到： INGREDIENTS: HONEY WITH CHILI PEPPERS. WARNING: DO NOT MICROWAVE IN THIS CONTAINER. DO NOT FEED HONEY TO INFANTS UNDER ONE YEAR.
OFF 的文字： Honey, chili peppers
```

### Tomato & calabrian chilli sauce

回收率 1.0　精確率 0.429

- 漏讀：—
- 多讀：adult, average, broken, button, consume, days, dry, end, energy, evident, intake, kcal

```
我們讀到： INGREDIENTS: Tomato, Partially Reconstituted Tomato, Tomato Purée, Cherry Tomato (5%), Lemon Juice from Concentrate, Sugar, Onion, Calabrian Chilli Purée (2%) [Chilli Purée, Salt, Acidity Regulator (Citric Acid), Antioxidant (Ascorbic Acid), Salt, Extra Virgin Olive Oil, Garlic Purée, Onion Powder, 
OFF 的文字： Tomato, Partially Reconstituted Tomato, Tomato Purée, Cherry Tomato (5%), Lemon Juice from Concentrate, Sugar, Onion, Calabrian Chilli Purée (2%) [Chilli Purée, Salt, Acidity Regulator (Citric Acid), Antioxidant (Ascorbic Acid Salt, Extra Virgin Olive Oil, Garlic Purée, Onion Powder, Basil, chilli p
```

## 全部

| 產品 | 回收率 | 精確率 | 漏讀 |
|---|---|---|---|
| Jalapeno hot sauce | 0.0 | 0.0 | bug, dietary, img, omcg, omg |
| Pepper sauce | 0.071 | 0.062 | acid, ascorbic, chloride, citric, distilled |
| Cholula Salsa Picante | 0.077 | 0.111 | agua, blanco, chiles, cido, especias |
| La Victoria Red Chile Sauce | 0.086 | 0.143 | aceite, agua, ajo, alimenticio, almid |
| hot sauce | 0.098 | 0.444 | apeppershs, baking, bre, buifits, call |
| Sriracha Hot Chili Sauce | 0.1 | 0.1 | chilis, essigs, kaliumsorbat, knoblauch, konservierungsmittel |
| Sambal Oelek | 0.111 | 0.2 | branntweinessig, johannisbrotkernmehl, meersalz, paprika, quot |
| Organic sriracha chili sauce | 0.111 | 0.333 | acetic, acid, garlic, gum, metabisulfite |
| Master, Fermented Chili Bean Sauce | 0.125 | 0.167 | chili, l-glutamate, monosodium, oil, salt |
| chili sauce | 0.163 | 0.667 | according, am-, are, ase, based |
| Sweet Chili Sauce | 0.174 | 0.211 | box, brands, call, canada, cap |
| Hot chilli sauce | 0.25 | 0.111 | msg, pepper, tomatoes |
| Chipotle Bitchin' Sauce | 0.25 | 0.056 | bitchin, chipotle, vegan |
| Avocado Hot Sauce - Original | 0.25 | 0.714 | black, coriander, cornflour, flavouring, garlic |
| lime chili sauce | 0.278 | 0.167 | dietary, efrigerate, food, how, igredients |
| Inca's food, aji panca paste | 0.286 | 0.154 | acid, benzoate, citric, panca, preservative |
| Chili Garlic Sauce | 0.286 | 0.364 | acetic, acid, corn, dehydrated, modified |
| Creamy garlic red pepper hot sauce | 0.3 | 0.667 | acid, bell, canola, citric, cumin |
| Cravin cajun hot sauce | 0.308 | 0.222 | alginate, distilled, guar, gums, louisiana |
| Mexico Lindo, Green Habanero Hot Sauce, Extra Hot | 0.333 | 0.455 | acid, antioxidant, benzonate, blue, citric |
| Fermented Chili Paste (Doubanjiang) | 0.357 | 0.312 | additives, beans, broad, flour, food |
| Squeeze Presser Creamy Buffalo Sauce | 0.373 | 1.0 | ail, all, amidon, arrel, call |
| Jalapeno hot sauce imp | 0.375 | 0.25 | gum, mash, pepper, water, xanthan |
| Golden Sriracha | 0.382 | 0.448 | bell, canola, corn, cream, cultured |
| CHILI CRISP | 0.39 | 1.0 | ail, arachides, chalote, contenir, contient |
| Franks Red Hot Original cayenne pepper sauce | 0.421 | 0.889 | any, bake, cistilled, combine, food |
| Green Chili Salsa Mild | 0.429 | 1.0 | ave, college, collins, com, compromise |
| Chili Garlic Sauce | 0.429 | 1.0 | acetic, acid, chili, corn, dehydrated |
| Matouk's, Hot Pepper Sauce, Salsa Picante | 0.435 | 0.526 | colour, corn, modified, mustard, oil |
| Chili sauce for burgers and dogs | 0.441 | 0.714 | ating, carbcnydrate, elled, how, ides |
| gochujang | 0.45 | 0.783 | anutrient, buyer, cerritos, com, dextrin |
| la michoacana mangohelada mango y chamoy | 0.452 | 0.7 | canula, cay, chi, cuar, equipment |
| Coney Island chili sauce | 0.466 | 1.0 | all, approximate, are, austin, based |
| Thai style green chili sauce | 0.471 | 0.762 | acidfey, caesga, che, cirka, geen |
| HOT HONEY HAM | 0.472 | 0.962 | call, color, comments, cst, date |
| Tomatillo Poblano Salsa | 0.5 | 0.667 | fbe, lmil, ohio, omcg, omg |
| P.F. Chang’s sriracha mayo | 0.5 | 0.842 | bate, cayenneer, dijon, eks, ents |
| Tahini Whole Seed Harissa | 0.5 | 0.214 | flavors, harissa, roasted |
| Louisiana sauce hot | 0.5 | 0.1 | aged, peppers |
| Hot Honey | 0.5 | 0.1 | jalapeno |
| Texas Style Hot Sauce | 0.5 | 1.0 | arving, cart, eno, omcg, omg |
| Born in Buffalo Wing Sauce | 0.5 | 0.444 | butter, oil, sauce, soybean |
| PERi PERi Sauce - Medium | 0.512 | 0.75 | bar, color, colors, com, due |
| Buffalo Medium Wing Sauce | 0.513 | 0.513 | anatto, dally, ded, dietary, ficant |
| Louisiana supreme hot sauce | 0.556 | 1.0 | box, com, louisiana, made, martinville |
| GOCHUJANG HOT PEPPER PASTE | 0.571 | 1.0 | defatted, hot, koji, pepper, salt |
| frank corriher chili sauce | 0.576 | 1.0 | chili, corrie, date, griculture, ispected |
| Chili sauce | 0.583 | 0.35 | chili, flavors, food, gum, xanthan |
| CHIPOTLE HOT SAUCE | 0.591 | 0.542 | acetic, apple, arbil, color, flavor |
| Hapi snacks, sriracha peas, spicy, chili garlic coated green | 0.594 | 0.594 | coconut, dimethyl-, essence, ethyl, ethyl- |
| xxx hot pepper sauce | 0.6 | 0.429 | choice, onions, peppers, red |
| Mango Habanero Sauce | 0.607 | 0.85 | caramel, distilled, flavor, gum, habanero |
| Hot Sauce | 0.625 | 1.0 | acetic, acid, apple, cider, flavor |
| Gochuchang | 0.632 | 0.414 | agricultural, derived, distilled, fermented, hot |
| Sweet Chilli Sauce | 0.643 | 0.818 | all, coloring, distill, faris, preservative |
| Mild wing sauce | 0.651 | 0.933 | anchorbar, cally, cayenne, com, gaoded |
| Mr. Bing CHILI CRISP | 0.656 | 0.875 | crunch, exper, horefrigeration, hummus, ili |
| TAOS HUM HOTSAUCE | 0.667 | 0.727 | farm, pepper, red, walking |
| Chipotle Bitchin' Sauce | 0.667 | 0.667 | aminos, bragg, grapeseed, lemon, liquid |
| schlotzskys hot sauce | 0.667 | 1.0 | austin, com, franchise, schlotzsky's, schlotzskys |
| RedHot Original Cayenne Pepper Sauce | 0.667 | 0.316 | aged, distilled, peppers |
| Sriracha Sauce/Salsa Sriracha (57800) | 0.688 | 0.733 | jalape, oil, soybean, spice, water |
| Mango Habanero Buffalo Wild Wings Sauce | 0.692 | 0.947 | concentrated, dehydrated, habanero, including, juce |
| Creamy Pepper Sauce | 0.696 | 1.0 | antonio, call, care, com, comments |
| Roasted poblano salsa cremo | 0.696 | 0.727 | addify, cilantro, odatel, odced, pobland |
| burman’s hot sauce | 0.7 | 0.5 | aged, distiller, peppers |
| Original Sichuan Chili Crisp | 0.7 | 0.913 | angeles, china, fly, jing, los |
| Chipotle Salsa Cremosa | 0.714 | 1.0 | acetic, acid, antioxidant, chipotle, iodate |
| Hot honey | 0.714 | 0.714 | habenero, ole |
| Chili Crisp Inspired Chicken Stick | 0.719 | 0.885 | beef, casing, collagen, cumin, mushroom |
| Fried chili oil | 0.727 | 1.0 | dioxide, sulfite, sulfur |
| Red Thai Style Chili Sauce | 0.733 | 1.0 | emios, per, peving, tosp |
| Mexican hot sauce | 0.75 | 0.75 | pepper, spice |
| CHILI GARLIC SAUCE | 0.75 | 0.6 | acetic, acia |
| Chili Seasame Oil | 0.75 | 0.3 | chillies |
| Hot Honey | 0.75 | 1.0 | vinegar |
| Sweet Chili Dipping Sauce | 0.757 | 1.0 | controues, fax, food, not, per |
| The Original Roasted Raspberry Chipotle Sauce | 0.76 | 0.864 | chili, dextrose, flavoring, fumaric, jalapeno |
| honey sriracha | 0.767 | 1.0 | cuisinart, fulham, group, license, registered |
| Organic Habanero pepper sauce | 0.769 | 0.909 | america, jalape, made |
| Pineapple Habanero Hot Sauce | 0.769 | 1.0 | acidleague, canada, com, crafted, guelph |
| Sriracha Sauce | 0.769 | 1.0 | brand, sauce, water |
| Cremosa Sauce Chipotle | 0.778 | 1.0 | call, cholula, com, hunt, mar |
| Piri Piri Molho | 0.778 | 0.438 | chilli, peppers |
| hooters wing sauce | 0.78 | 0.886 | clearwater, diglyc, foods, lecith, manufacturfd |
| Honey Harissa Salad With Turkey & Couscous | 0.783 | 0.855 | aged, cayenne, corn, dehydrated, flavored |
| Avocado Serrano Hot Sauce | 0.786 | 0.815 | chili, jalapeno, pepper, preservatives, rosemary |
| Creamy Buffalo Sauce | 0.792 | 0.905 | distile, fla, mustard, springfield, way |
| Hot Honey Chicken Salad | 0.794 | 0.9 | eggs, fre, gun, olived, paprikal |
| Sweetened Chili Sauce For Spring Roll | 0.8 | 0.889 | correcteur, d'acidit |
| Jalapeño Pepper Salsa Verde | 0.8 | 0.857 | cilantro, jalapeno, tomatoes |
| Maui Tiger Shark Sauce | 0.8 | 0.923 | gluten-free, msg, spices |
| Sweet Chili Sauce | 0.812 | 1.0 | cor, modified, promed |
| Cholula hot sauce sweet habanero | 0.812 | 0.867 | ascorbic, citric, dehydrated |
| Baja Chipotle Sauce | 0.812 | 0.867 | lime, paprika, sorbate, spice, spices |
| Hot Sauce, Habanero | 0.818 | 0.243 | carrots, spices |
| Gia russa, select pasta sauce, hot sicilian | 0.818 | 0.209 | imported, plum |
| kinder garlic Parmesan wing sauce | 0.824 | 1.0 | acidi, creek, kinder, not, produced |
| SRIRACHA HOT CHILI SAUCE | 0.833 | 1.0 | ingr, sulphite |
| Original Hot Sauce | 0.833 | 0.909 | aged, water |
| Black Hot Sauce &quot;Capitan Gourmet&quot; | 0.84 | 0.933 | alsa, citrico, com, comm, ingredientes |
| Simple Truth Organic Sweet Thai Style Chili Sauce | 0.84 | 0.875 | jalape, lue, pine, pple |
| Chilli Garlic Sauce | 0.842 | 0.842 | acacia, preservatives, stabilisers |
| medium serrano pepper salsa | 0.846 | 0.917 | rano, ser |
| Green Pepper Sauce | 0.857 | 0.667 | freshness, quot |
| Organic Chickpea Puffs, Sriracha Sunshine | 0.857 | 0.783 | pepper, red, seasoning |
| PERi-PERi Sauce | 0.862 | 1.0 | alginate, derived, glycol, propylene |
| SPICY CHILI CRISP | 0.867 | 1.0 | condition, refrigerated |
| GOCHUJANG PASTE | 0.868 | 0.917 | allergy, bold, pur, suitable, vegans |
| Sweet Sauce For Spring Roll | 0.875 | 0.875 | turnip |
| Sweet & Spicy Thai Chili Dipping Sauce | 0.875 | 0.913 | jalape, per, tbsp |
| the bossy gourmet hatch red Chile sauce | 0.875 | 0.933 | heat, serve |
| Sweet Honey Flovored Wing Sauce | 0.875 | 1.0 | ados, quot, trivial |
| Buffalo Sauce Made With Avocado Oil | 0.875 | 0.933 | nuts, tree |
| Global Hot Sauce | 0.875 | 0.977 | chile, garl, garli, leoresin, soc |
| Julios serrano salsa | 0.882 | 1.0 | it's, way |
| Sweet Chili Sauce | 0.882 | 1.0 | contribu, food |
| Hot sauce ounce | 0.882 | 1.0 | produces, www |
| Restaurant Style Salsa Medium | 0.882 | 0.938 | paste, pur |
| SRIRACHA HOT SAUCE | 0.889 | 0.727 | jalapenos |
| Wing Sauce & Dip Bourbon Peach BBQ | 0.889 | 1.0 | creek, kinder, produced, walnut |
| Sichuan Chili Sauce | 0.889 | 1.0 | black, vinegar |
| Camouflage Hot Sauce | 0.889 | 0.471 | cayenne |
| Hot & sweet tomato chili sauce | 0.889 | 1.0 | milk, nut |
| Total insanity hot sauce | 0.895 | 0.944 | berry, black |
| Hot Sauce | 0.9 | 0.9 | sale |
| GREEN CHILE Enchilada Sauce | 0.903 | 1.0 | mills, minneapolis, sales |
| Ghost Pepper Habanero | 0.905 | 1.0 | diced, tomaties |
| Lkk chilli bean sauce | 0.905 | 0.613 | beans, pepper |
| Chili Crisp | 0.905 | 0.792 | hot, tamariane |
| Crunchy Roasted Edamame Sriracha | 0.909 | 0.909 | chilli |
| Tobasco | 0.909 | 0.769 | jalape |
| Organic Habanero Pepper Sauce | 0.909 | 1.0 | arganic |
| Burman's original cayenne pepper hot sauce | 0.909 | 0.909 | granulated |
| Hot Sauce | 0.909 | 0.833 | ascetic |
| Wegmans Organic Red Sriracha | 0.909 | 0.909 | jalapen |
| Hot Sauce | 0.909 | 1.0 | ner |
| Original tiger sauce bottle | 0.913 | 0.84 | foods, reily |
| SRIRACHA HOT CHILI SAUCE | 0.917 | 1.0 | bisufite |
| Blue Agave Sriracha | 0.917 | 0.846 | peppers |
| Nacho cheese sauce | 0.922 | 0.839 | dehydrated, enzyme, jalapeno, low |
| Salsa | 0.923 | 0.923 | jalape |
| Hot Sauce | 0.923 | 0.923 | xanthan |
| The Classic Hot Sauce garlic fresno addition | 0.923 | 1.0 | spicy |
| Red Sriracha chili sauce | 0.923 | 0.923 | jalape |
| Harissa green chile | 0.927 | 1.0 | including, seasoning, spices |
| Low calorie sweet chili sauce | 0.93 | 0.87 | dextrin, jalape, oleoresin |
| Thai Sriracha | 0.931 | 1.0 | nut, ots |
| Gourmet asian sauces | 0.933 | 0.933 | extractives |
| All spice cafe, cayenne habanero sauce | 0.933 | 0.933 | venegar |
| Horseshoe Brand Kiwi Jalapeño Hot Sauce | 0.938 | 0.938 | jalapeno |
| Fritos Hot Bean Dip | 0.938 | 0.882 | jalape |
| Hot Sauce | 0.941 | 0.889 | sot |
| Green Sriracha Sauce (57931) | 0.941 | 1.0 | roasted |
| hot sauce chipotle | 0.941 | 1.0 | morita |
| GOTCHU Korean Hot Sauce | 0.941 | 1.0 | preserva, tive |
| Hot sauce | 0.941 | 0.8 | starch-modified |
| HT Traders Chipotle Salsa | 0.941 | 0.97 | jalape, onon |
| Chunky Garlic & Jalapeño Hot Sauce | 0.941 | 0.941 | jalapeno |
| Cheez doodles baked puffs hot & honey | 0.943 | 0.82 | annatto, bter, owder |
| Melinda's Chipotle Habanero Pepper Sauce, 5 Ounce | 0.944 | 1.0 | mash |
| Original Buffalo Sauce | 0.947 | 1.0 | distilled |
| Wing Sauce & Dip | 0.952 | 0.952 | jalapeno |
| Hellfire Green Gourmet | 0.957 | 0.917 | tomatoes |
| Red Enchilada Sauce | 0.957 | 1.0 | cup |
| Wing Sauce & Dip | 0.96 | 0.96 | jalape |
| Sweet chili sauce | 0.96 | 0.96 | lodized |
| HOT HONEY ORGANIC HOMMUS | 0.96 | 0.96 | tbsp |
| Kickin' Chipotle Sauce | 0.966 | 0.933 | pepper |
| Datil Pepper Hot Sauce | 0.971 | 1.0 | fish |
| CHIPOTLE CREAMY SAUCE | 0.973 | 0.923 | acocium |
| Creamy pepper sauce | 0.975 | 1.0 | quot |
| Mild buffalo wing sauce | 0.976 | 0.891 | anchowy |
| Wing sauce | 0.978 | 0.957 | mono |
| Chunky Habanero Salsa Hot | 1.0 | 1.0 | — |
| Wing sauce and dip | 1.0 | 1.0 | — |
| Ghost Pepper Sauce | 1.0 | 1.0 | — |
| Sriracha Hot Chili Sauce | 1.0 | 1.0 | — |
| Ritz Crackers Hot Honey | 1.0 | 1.0 | — |
| Hot Honey | 1.0 | 0.25 | — |
| Roasted Pineapple Habanero Sauce | 1.0 | 1.0 | — |
| Hot Honey Crackers | 1.0 | 0.9 | — |
| Sriracha chili sauce | 1.0 | 1.0 | — |
| WING SAUCE & DIP BUTTERY BUFFALO | 1.0 | 1.0 | — |
| Spicy jalapeño hot sauce | 1.0 | 1.0 | — |
| Ground Zero Hot Sauce | 1.0 | 1.0 | — |
| Pop Daddy Hot Sauce Pretzels | 1.0 | 1.0 | — |
| Wing sauce sticky honey BBQ | 1.0 | 1.0 | — |
| Picante Sauce | 1.0 | 1.0 | — |
| Chili Sauce rot | 1.0 | 1.0 | — |
| Sriracha | 1.0 | 0.963 | — |
| Roasted Chipotle Salsa | 1.0 | 1.0 | — |
| Harissa, Pepper Sauce | 1.0 | 1.0 | — |
| HABANERO HOT SAUCE | 1.0 | 1.0 | — |
| 57 sauce | 1.0 | 1.0 | — |
| hot sauce | 1.0 | 1.0 | — |
| Sweet Chili Sauce | 1.0 | 1.0 | — |
| Hot Sauce Chile Habanero | 1.0 | 1.0 | — |
| Rasta Fire - Orange Krush - The Habanero Sauce | 1.0 | 0.95 | — |
| Southern Sriracha Spicy Honey | 1.0 | 1.0 | — |
| Mystery hot sauce | 1.0 | 1.0 | — |
| Cholula Hot Sauce Original | 1.0 | 0.609 | — |
| HOT SAUCE | 1.0 | 1.0 | — |
| Great Value Thai Style Sweet Chili Sauce | 1.0 | 0.706 | — |
| THAI SWEET CHILI SAUCE | 1.0 | 1.0 | — |
| Mike's Hot Honey | 1.0 | 1.0 | — |
| Yuzu Kosho Hot Sauce | 1.0 | 1.0 | — |
| Humboldt hotsauce | 1.0 | 1.0 | — |
| Sweet & Spicy Sriracha Sauce | 1.0 | 0.722 | — |
| Mango habanero pepper sauce imp | 1.0 | 1.0 | — |
| Original habanero pepper sauce | 1.0 | 1.0 | — |
| Red hot dill pickle | 1.0 | 0.952 | — |
| HOT TACO SAUCE | 1.0 | 1.0 | — |
| Gochujang | 1.0 | 1.0 | — |
| Honey barbecue wing sauce | 1.0 | 1.0 | — |
| AF Chili Chunka Sambal | 1.0 | 1.0 | — |
| Zesty Buffalo Sauce | 1.0 | 0.966 | — |
| Buffalo Sauce | 1.0 | 0.9 | — |
| taco bell chipotle creamy sauce | 1.0 | 0.905 | — |
| Tabasco® | 1.0 | 0.833 | — |
| Hot Honey Garlic Chicken Stir-Fry | 1.0 | 0.795 | — |
| Tuong ot | 1.0 | 1.0 | — |
| Green Chili Paste | 1.0 | 1.0 | — |
| sweet chili sauce | 1.0 | 1.0 | — |
| Thai style sweet chili sauce | 1.0 | 1.0 | — |
| Sriracha hot chili sauce imp | 1.0 | 1.0 | — |
| Marco polo, ajvar, red pepper spread | 1.0 | 1.0 | — |
| Siriracha Hot Chili Sauce | 1.0 | 1.0 | — |
| Redhot wings | 1.0 | 1.0 | — |
| Thai Ger Sweet Chili Sauce | 1.0 | 1.0 | — |
| Hot sauce | 1.0 | 1.0 | — |
| Blue Agave Sriracha | 1.0 | 1.0 | — |
| Original Sichuan Chili Crisp | 1.0 | 0.947 | — |
| Roasted Chile Verde Pan Sauce | 1.0 | 1.0 | — |
| Chipotle fire hot sauce | 1.0 | 0.917 | — |
| Tyson Hot Honey Wings | 1.0 | 1.0 | — |
| Habanero Condiment | 1.0 | 1.0 | — |
| Sriracha sauce | 1.0 | 1.0 | — |
| Crybaby Craig's Hot Honey | 1.0 | 1.0 | — |
| BEAN SALSA HABANERO CORN BAR | 1.0 | 1.0 | — |
| Chipotle Hot Sauce | 1.0 | 1.0 | — |
| Spicy Garlic Hot Sauce | 1.0 | 0.966 | — |
| Kickin' Garlic Buffalo Hot Sauce | 1.0 | 1.0 | — |
| RedHot Original imp | 1.0 | 1.0 | — |
| Hot Sauce | 1.0 | 1.0 | — |
| Habanero Salsa | 1.0 | 1.0 | — |
| Original Cayenne Pepper Sauce | 1.0 | 1.0 | — |
| Traditional Tunisian Harissa Hot Chili Pepper Paste with Her | 1.0 | 1.0 | — |
| hot pepper sauce | 1.0 | 0.81 | — |
| Hot Honey | 1.0 | 0.643 | — |
| Smokin' Hot, Jalapeno Pepper Sauce | 1.0 | 0.75 | — |
| soarky wing sauce | 1.0 | 1.0 | — |
| Hot and Sweet tomato chili sauce | 1.0 | 1.0 | — |
| Green jalapeno pepper puree | 1.0 | 1.0 | — |
| Scorpion pepper sauce | 1.0 | 1.0 | — |
| Chunky Salsa Mild | 1.0 | 0.923 | — |
| SMOKY CHIPOTLE HOT SALSA | 1.0 | 1.0 | — |
| Ring of Fire Original | 1.0 | 1.0 | — |
| Gochujang | 1.0 | 1.0 | — |
| Gochujang Paste | 1.0 | 1.0 | — |
| CHILI GARLIC SAUCE | 1.0 | 0.909 | — |
| Corn and Chile Tomato-Less Salsa | 1.0 | 1.0 | — |
| Harissa Aioli | 1.0 | 0.974 | — |
| asian style sweet chili wing sauce | 1.0 | 0.628 | — |
| Bb sauce chipotle pineapple | 1.0 | 1.0 | — |
| Sweet Chili Sauce | 1.0 | 0.833 | — |
| Chili Seasoning | 1.0 | 0.667 | — |
| Green habanero pepper sauce | 1.0 | 1.0 | — |
| Verde Hot Sauce | 1.0 | 1.0 | — |
| Ghost pepper gourmet salsa, ghost pepper, hot | 1.0 | 0.64 | — |
| Chili paste | 1.0 | 0.733 | — |
| Creamy Style Ghost Pepper Wing Sauce and Condiment | 1.0 | 1.0 | — |
| Black Magic | 1.0 | 1.0 | — |
| Original Cayenne Pepper Sauce | 1.0 | 1.0 | — |
| Buffalo wing sauce | 1.0 | 1.0 | — |
| Thai Style Sweet Chili Sauce | 1.0 | 0.536 | — |
| Honey Sriracha Chicken | 1.0 | 1.0 | — |
| Fire Roasted Garlic & Habanero Sauce | 1.0 | 1.0 | — |
| Kari Kari - Garlic Chili Crisp | 1.0 | 0.6 | — |
| Green pepper hot sauce | 1.0 | 0.933 | — |
| Salsa picante | 1.0 | 1.0 | — |
| Hot Dog Chili Sauce | 1.0 | 1.0 | — |
| Bottle da bomb beyond insanity hot sauce | 1.0 | 1.0 | — |
| Coconut mango pepper sauce | 1.0 | 1.0 | — |
| Chickpea Puffs, Conventional Non GMO, Sriracha | 1.0 | 1.0 | — |
| Salsa Macha Chilis, Peanuts, Pepitas | 1.0 | 0.929 | — |
| Hot Honey with Crisp Chili-dipping sauce | 1.0 | 1.0 | — |
| La victoria salss mild | 1.0 | 0.929 | — |
| California Chili Hot Sauce | 1.0 | 1.0 | — |
| Hot Sauce | 1.0 | 1.0 | — |
| Fiery habanero sauce | 1.0 | 0.909 | — |
| Tomato & calabrian chilli sauce | 1.0 | 0.429 | — |
| Chili Garlic Sauce | 1.0 | 0.818 | — |
| Nando's Garlic Peri Peri Sauce 135G | 1.0 | 1.0 | — |
| Parmesan garlic wing sauce | 1.0 | 0.82 | — |
| Original | 1.0 | 1.0 | — |
| Habanero Hot Sauce | 1.0 | 1.0 | — |
| Absolute Yummy Hot Chili Oil | 1.0 | 0.5 | — |
| Sriracha Hot Chili Sauce | 1.0 | 0.9 | — |
| Honey Sesame Sauce | 1.0 | 0.667 | — |
| Tomato sauce | 1.0 | 1.0 | — |
| Chipotle Peppers in Adobo Sauce | 1.0 | 1.0 | — |
| Hot sauce imp | 1.0 | 1.0 | — |
| Hot Honey Scotch Bonnet And Habanero | 1.0 | 1.0 | — |
| Thai Sweet Chili Sauce | 1.0 | 1.0 | — |
| CHILI GARLIC SAUCE | 1.0 | 1.0 | — |
| Hot Honey | 1.0 | 1.0 | — |
| Mike's Hot Honey Extra Hot | 1.0 | 1.0 | — |
| Green Chile Sauce | 1.0 | 1.0 | — |
| Big Red's Smokey Habanero Sauce | 1.0 | 1.0 | — |
| Buffalo Hot Sauce | 1.0 | 1.0 | — |
| Hot Sauce Chile Habanero | 1.0 | 1.0 | — |
| Frank's Red Hot Original | 1.0 | 0.818 | — |
| RedHot Wings Sauce Buffalo | 1.0 | 1.0 | — |
| Sriracha chili sauce, spicy and garlic | 1.0 | 0.938 | — |
| Chamoy Peach Rings | 1.0 | 1.0 | — |
| franks red hot | 1.0 | 1.0 | — |
| Chicken Diced in Mild Chipotle Sauce | 1.0 | 1.0 | — |
| Griffins wing sauce | 1.0 | 1.0 | — |
| Pain is Good | 1.0 | 0.952 | — |
| Chipotle Peppers in Adobe Sauce | 1.0 | 1.0 | — |
| Sweet Potato Habanero Hot Sauce | 1.0 | 0.957 | — |
| Mild Sauce | 1.0 | 1.0 | — |
| Hill Country Fare Louisiana Hot Sauce | 1.0 | 1.0 | — |
| Salsa picante | 1.0 | 1.0 | — |
| Mina, harissa moroccan red pepper sauce, spicy | 1.0 | 1.0 | — |
| Hot sauce | 1.0 | 0.9 | — |
| apple smoked habanero | 1.0 | 1.0 | — |
| apple smoked habanero | 1.0 | 1.0 | — |
| Hot Sauce | 1.0 | 1.0 | — |
| chili bean sauce (Toban djan) | 1.0 | 1.0 | — |
| RedHot Wings Sauce Buffalo | 1.0 | 1.0 | — |
| CHICKEN SRIRACHA BAR | 1.0 | 1.0 | — |
| Hot sauce | 1.0 | 1.0 | — |
| Ghost Pepper Naga Jolokia Hot Sauce | 1.0 | 0.882 | — |
| Chili Sauce | 1.0 | 1.0 | — |
| Jalapeño Sauce | 1.0 | 1.0 | — |
| New Mexico Style Enchilada Sauce | 1.0 | 1.0 | — |
| Cooking hot sauce | 1.0 | 1.0 | — |
| Gringo bandito, sauce, hot | 1.0 | 0.929 | — |
| Hot sauce | 1.0 | 1.0 | — |
| Sriracha Hot Sauce | 1.0 | 1.0 | — |
| Hot sauce | 1.0 | 1.0 | — |
| Wing Sauce & Dip Sticky Honey BBQ | 1.0 | 1.0 | — |
| Gochujang Korean chili sauce | 1.0 | 1.0 | — |
| Sweet Chili Sauce | 1.0 | 1.0 | — |
| Jalapeno Pepper Hot Sauce | 1.0 | 1.0 | — |
| sriracha hot chilli sauce | 1.0 | 1.0 | — |
| Green Dragon Hot Sauce | 1.0 | 1.0 | — |
| Pace Picante | 1.0 | 1.0 | — |
