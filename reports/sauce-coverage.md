# 產品召回率（A17）

規則版本 `v1`　清單 74 筆　命中 58 筆　**recall = 0.7838**（門檻 0.9）

清單是 held-out 的：它在抓取設定定稿之前建立，抓取端看不到它（A18）。

## 未命中

漏收一款辣醬，事後完全看不出來——查不到與不存在長得一模一樣。
所以每一筆未命中都要寫出「本來哪一個來源階層應該收到它」，那才是要修的地方。

| 名稱 | 品牌 | 品牌在總表裡？ | 清單來源 | 本來應該由誰收到 |
|---|---|---|---|---|
| Original Red Sauce | Tabasco | 有 | analyst_recall | （來源不明） |
| Hotter Hot Sauce | Truff | 有 | analyst_recall | （來源不明） |
| XXXtra Hot Habanero Sauce | El Yucateco | 有 | analyst_recall | （來源不明） |
| Bee Sting Honey | Bushwick Kitchen | 有 | analyst_recall | （來源不明） |
| Small Axe Peppers Bronx Greenmarket Hot Sauce | Small Axe Peppers | 有 | analyst_recall | （來源不明） |
| Pineapple Jalapeno | Adoboloco | 沒有 | analyst_recall | （來源不明） |
| Hamajang | Adoboloco | 沒有 | analyst_recall | （來源不明） |
| Zombie Apocalypse | CaJohns | 沒有 | analyst_recall | （來源不明） |
| Trinidad Scorpion | CaJohns | 沒有 | analyst_recall | （來源不明） |
| Rogue Ghost Pepper | High River Sauces | 有 | analyst_recall | （來源不明） |
| Pineapple Express | Volcanic Peppers | 有 | analyst_recall | （來源不明） |
| Hot Sauce Verde | Fat Cat Gourmet | 沒有 | analyst_recall | （來源不明） |
| Salsa Valentina | Valentina | 有 | analyst_recall | （來源不明） |
| Salsa Búfalo Clásica | Búfalo | 有 | analyst_recall | （來源不明） |
| Iguana Original Red | Iguana | 有 | analyst_recall | （來源不明） |
| Pain Is Good Batch 37 | Pain Is Good | 有 | analyst_recall | （來源不明） |

「品牌在總表裡＝有」的那幾筆，漏的是**這一款**，不是這個品牌——
多半是通路只上架了同品牌的其他口味。「沒有」才是整個品牌都沒收到。

## 命中

比對級別分佈：{'brand+overlap': 30, 'brand+product': 19, 'product_only': 9}

| 名稱 | 品牌 | 比對方式 | 對到的產品名 | 來源 |
|---|---|---|---|---|
| Green Jalapeno Sauce | Tabasco | brand+overlap | ® brand green pepper sauce | fdc|off |
| Habanero Sauce | Tabasco | brand+overlap | HABANERO HOT! SAUCE | fdc|off |
| Chipotle Pepper Sauce | Tabasco | brand+product | CHIPOTLE PEPPER SAUCE | fdc|off |
| Original Cayenne Pepper Sauce | Frank's RedHot | brand+product | ORIGINAL CAYENNE PEPPER SAUCE | fdc|off |
| Buffalo Wings Sauce | Frank's RedHot | brand+overlap | RedHot Wings Sauce Buffalo | off |
| Original Hot Sauce | Cholula | brand+product | Original hot sauce | off |
| Chipotle Hot Sauce | Cholula | brand+product | CHIPOTLE HOT SAUCE | off |
| Green Pepper Hot Sauce | Cholula | brand+product | GREEN PEPPER HOT SAUCE | fdc|off |
| Louisiana Hot Sauce | Crystal | product_only | Louisiana hot sauce | fdc|off |
| Original Louisiana Hot Sauce | Louisiana Brand | brand+overlap | THE ORIGINAL SOUTHWEST JALAPENO HOT SAUCE | fdc |
| Sriracha Hot Chili Sauce | Huy Fong Foods | brand+product | Sriracha Hot Chili Sauce | fdc|off |
| Chili Garlic Sauce | Huy Fong Foods | brand+overlap | Hot Chili Sauce Sriracha Packets, 7 gram Packets | fdc |
| Sambal Oelek | Huy Fong Foods | brand+product | SAMBAL OELEK | fdc |
| Original Habanero Hot Sauce | Secret Aardvark | brand+overlap | Aardvark Habanero Hot Sauce | off |
| Serrabanero Green Hot Sauce | Secret Aardvark | brand+product | Serrabanero Green Hot Sauce | shopify |
| Habanero Condiment | Yellowbird | brand+product | Habanero Condiment | off |
| Serrano Condiment | Yellowbird | brand+product | Serrano condiment sauce | off |
| Jalapeno Condiment | Yellowbird | brand+product | Jalapeno condiment | off |
| Original Black Truffle Hot Sauce | Truff | brand+overlap | Jalapeno Lime Black Truffle Infused Sauce | off |
| Original Habanero Pepper Sauce | Melinda's | brand+product | Original habanero pepper sauce | off |
| XXXtra Hot Habanero | Melinda's | brand+overlap | Melinda’s Original Habanero XXXtra Hot Sauce (Gallon) | shopify |
| Green Habanero Hot Sauce | El Yucateco | brand+overlap | CHILE HABANERO HOT SAUCE | fdc|off |
| Red Habanero Hot Sauce | El Yucateco | brand+overlap | CHILE HABANERO HOT SAUCE | fdc|off |
| Habanero Pepper Sauce | Marie Sharp's | brand+product | Habanero Pepper Sauce | off |
| Fiery Hot Habanero Sauce | Marie Sharp's | brand+overlap | Fiery habanero sauce | off |
| Pineapple Habanero | Queen Majesty | product_only | PINEAPPLE HABANERO SAUCE | fdc|off |
| Scotch Bonnet and Ginger | Queen Majesty | brand+overlap | Scotch Bonnet & Ginger Hot Sauce | shopify |
| Red Habanero Hot Sauce | Heartbeat Hot Sauce | brand+overlap | Hot Ones Jr. The Red | Hot Ones Hot Sauce -C | shopify |
| Pineapple Habanero Hot Sauce | Heartbeat Hot Sauce | product_only | PINEAPPLE HABANERO SAUCE | fdc|off |
| Insanity Sauce | Dave's Gourmet | brand+overlap | Total insanity hot sauce | off |
| Ghost Pepper Naga Jolokia Hot Sauce | Dave's Gourmet | brand+overlap | Ghost pepper hot sauce | off |
| Reaper Squeezins | Puckerbutt Pepper Company | brand+product | Reaper Squeezins | shopify |
| The Last Dab Apollo | Heatonist | brand+product | The Last Dab Apollo | shopify |
| Los Calientes Rojo | Heatonist | product_only | Los Calientes Rojo | shopify |
| Hot Honey | Mike's Hot Honey | brand+overlap | Mike's Hot Honey | off |
| Brooklyn Delhi Roasted Garlic Achaar | Brooklyn Delhi | brand+overlap | Roasted Garlic Achaar | shopify |
| Kampot Pepper Hot Sauce | Bravado Spice | brand+overlap | Ghost pepper and blueberry hot sauce | off |
| Black Garlic Carolina Reaper | Bravado Spice | brand+overlap | Black Garlic Carolina Reaper Hot Sauce - Hot Ones Season 6 | shopify |
| Da Bomb Beyond Insanity | Da Bomb | product_only | DA' BOMB BEYOND INSANITY HOT SAUCE | webshop |
| Sriracha | Yellowbird | brand+product | Sriracha Hot Sauce | off|shopify |
| Garlic Reaper | Torchbearer Sauces | brand+overlap | Garlic Reaper™ - Carolina Reaper garlic hot sauce - Case of 12 | shopify |
| Zombie Apocalypse Hot Sauce | Torchbearer Sauces | brand+overlap | Zombie Apocalypse™ - Ghost Pepper Hot Sauce - Case of 12 | shopify |
| Tears of the Sun | High River Sauces | brand+product | Tears of the Sun | off|shopify |
| Karma Sauce Extreme Karma | Karma Sauce | brand+overlap | Funken Yellow - Yellow Moruga Edition | Karma Sauce -C | shopify |
| Cosmic Disco | Karma Sauce | brand+product | Cosmic Disco | shopify |
| Lucky Dog Year of the Dog | Lucky Dog Hot Sauce | brand+overlap | Year of the Dog - Thai Chile Pineapple Hot Sauce - HOT | shopify |
| Red Clay Original Hot Sauce | Red Clay | brand+overlap | Pantry Pairing: Jimmy Red Corn Grits + Original Hot Sauce | shopify |
| Salsa Macha | Masienda | product_only | Salsa Macha | off |
| Chili Crisp | Fly By Jing | brand+overlap | Original Sichuan Chili Crisp | off |
| Sichuan Chili Crisp | Lao Gan Ma | product_only | Sichuan Chili Crisp | off |
| Gochujang Hot Sauce | Bibigo | brand+product | Gochujang | off |
| Harissa | Mina | brand+overlap | harissa moroccan red pepper sauce, spicy | off |
| Piri Piri Sauce | Nando's | product_only | Piri-Piri Hot Sauce | off |
| Salsa Huichol | Huichol | product_only | Salsa Huichol Hot Sauce | off |
| Tapatio Salsa Picante | Tapatio | brand+overlap | SALSA PICANTE HOT SAUCE | fdc|off |
| Blair's After Death Sauce | Blair's | brand+overlap | After Death Sauce | shopify |
| Sweet Ghost Pepper Sauce | Dawson's | brand+overlap | Sichuan Ghost Pepper Sauce | off|shopify |
| Hellfire Devil's Gold | Hellfire Hot Sauce | brand+overlap | Limited Edition Hellfire Hot Sauce "Devil's Gold" Custom diecast Hot Wheels Car. | shopify |
