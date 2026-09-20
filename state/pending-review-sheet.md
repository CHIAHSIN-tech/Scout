# 待審的 20 筆（第三版：分層取樣 ＋ 排除食譜 ＋ prompt v3）

檔案：`sauce/prompts/sauce-review-verdict/golden.pending.jsonl`
審法：每一列把 `reviewed` 改成 `true`；`expected` 不對就直接改它。

審的時候要看的是**這句話是不是那篇評論對那款醬的重點**——
「引文出自原文」已經由機器驗過（A25），那一層不用你看。

**這一批：20 篇、抽出 62 筆評語、17 篇通過三層驗證。**

## 1. The 3 Trader Joe's Hot Sauces to Get Before the World Catches On

**驗證沒過**：verdicts[2] 的 quote 不是正文的子字串（不可以改寫）

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Chili Onion Crunch | descriptive | 3 out of 10 | Trader Joe’s take is called Chili Onion Crunch , a tamer version than the Chinese original (TJ’s product does not contain nuts). It’s less spicy and stored in olive oil, and it dials up the garlic and |
| Italian Bomba Hot Pepper Sauce | positive | 7.5 out of 10 | My favorite of the bunch and also the spiciest, Italian Bomba Hot Pepper Sauce is Calabrian chile peppers that have been fermented and mixed to a smooth paste. There’s a hint of tang, a hint of savori |
| Harissa | descriptive | 6 out of 10 | Trader Joe’s version keeps its harissa basic, with the standard spices of caraway seeds, garlic, and coriander. Harissa will wake up most vegetables—especially carrots —or enliven a dish like braised  |

## 2. How Austin Hot Sauce Brands Are Solving the Great Sriracha Shortage

**驗證沒過**：verdicts[0] 的 sauce_name_raw 'Yellowbird’s Blue Agave sriracha' 不在正文裡

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Yellowbird’s Blue Agave sriracha | descriptive | — | Yellowbird’s take on that challenge resulted in Blue Agave sriracha, which Milton’s team makes with all-natural ingredients like red jalapeños, blue agave nectar, organic vinegar, garlic, and lime jui |
| Diamondback’s Texafied sriracha | descriptive | — | The “Texafied” aspect of Diamondback comes courtesy of its higher heat level, which is balanced by a higher sweetness level. The combination of the two, along with a distinct umami funk provided by th |
| ATX Hot Sauce’s Texas sriracha | descriptive | — | ATX Hot Sauce’s Texas sriracha includes a number of unique ingredients, from plums to cardamom to cane sugar. As far as the “Texas” element is concerned, McClellan’s team uses dried ancho chiles (a be |

## 3. The 10 Best Chili Crisps, According to Bon Appétit Editors

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Lao Gan Ma Spicy Chili Crisp | positive | — | Every bite is the Platonic ideal of what a chili crisp should be: crunchy, spicy (but not too spicy), and versatile enough to put on everything. |
| Mẹ’s Way Chili Sauce | positive | — | This Vietnamese-style condiment is plenty spicy, but it's the savory funk of fish sauce that sets it apart from the pack. |
| S&B Crunchy Garlic with Chili Oil | positive | — | Heaps of garlic, crisp as a potato chip; toasty ground sesame seeds; bits of almonds; and loads of MSG —a tasty treasure trove for texture addicts. |
| Fly by Jing Sichuan Chili Crisp | positive | — | Thanks to fermented black beans, mushroom powder, and seaweed, it has an endless umami flavor. And the smoky-tingly heat, attributable to both spicy chiles and numbing Sichuan peppers, is at just the  |
| Junzi Original Chili Oil Pack | mixed | — | While I’m normally of the opinion “ the crunchier the chili crisp , the closer to heaven,” Junzi’s house-made chili oil is less crispy than others on this list, but it always has a special place in my |
| Mama Teav’s Hot Garlic Chili Crisp | positive | — | The crisp factor is real: I find that this condiment has far more texture than most on the market and leans more savory than sweet. |
| The Bits Chili Oil | positive | — | Made in west Los Angeles out of the home of Susan and Mike Wong, the oil actually has a consistency more like a spread, making it perfect to slip into almost any dish for a flavorful, garlic-forward u |
| Loud Grandma CBD Chili Crisp Oil | positive | — | this complex chili crisp was crafted to tingle your tongue and please your palate while imparting the mind relaxing and stress reducing effects of cannabidiol. |
| Liquid Fire | positive | — | For me, this Filipinx-owned company’s condiment has the ideal level of heat: enlivening but not overwhelming. |

## 4. Best Hot Sauce Gift Sets for Lovers of Spice

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Gringo Bandito Hot Sauce Classic Variety Pack | descriptive | — | Alternative music fans will enjoy this set of four hot sauces from the lead singer of The Offspring. It comes with original red, green habanero, spicy yellow, and super hot varieties, all in 5-ounce b |
| Yellowbird Hot Sauce Variety Pack | descriptive | — | Yellowbird sauces are described as a condiment, and their thickness and squeeze bottles back that up. They’re full of bright flavors from ingredients like tangerine, cucumber, and carrot. |
| The Good Hurt Fuego Hot Sauce Gift Set | descriptive | — | Seven bottles of sauce will keep your giftee happy for a while with this set, cleverly packaged to look like TNT. Smoky bourbon, whiskey habanero, and ghost pepper are some of the flavors. |
| PuckerButt Smokin’ Ed’s Special Reserve Super Hot Gift Set | descriptive | — | The man behind PuckerButt also created the Carolina Reaper pepper, and you can try it in this pack of five of their reserve sauces. It includes Reaper Squeezins with Carolina Reaper, Gator Sauce, and  |
| Marie Sharp’s Hot Sauce Variety 6-Pack | positive | — | Marie Sharp’s Belizean Heat won our hot sauce taste test with its bright, fresh flavor and fruity habanero heat. Get it in this variety pack, along with five other varieties from the popular brand. |
| Ass Kickin’ Challenge Box | descriptive | — | This set is not just hot sauces — it’s an experience. Each of the 12 sauces includes steps up in heat, so your giftee can gather his or her friends and see who can go the furthest without sweating or  |
| Melinda’s Habanero Hot Sauce Variety Pack | descriptive | — | Melinda’s sauces are high on flavor but relatively mild on heat, so this is a great set to get for a hot sauce beginner. They’re habanero-based and include mango, garlic, and extra hot varieties. |
| El Yucateco Hot Sauce Variety Pack | positive | — | El Yucateco tied for runner-up in our hot sauce taste test , and it’s great for topping any Mexican or Caribbean food. The variety pack has six sauces, all habanero-based, including the well-regarded  |
| Secret Aardvark Hot Sauce Sampler | descriptive | — | Secret Aardvark has a devoted following, and their habanero hot sauce is complex and salsa-like. The other sauces in this sampler include a green habanero sauce, a Chinese-influenced garlic and black  |
| Keith’s Hot Sauce Trio | descriptive | — | Keith’s sauces have a lot of flavor and are designed for specific foods, so they’re great for beginners. You’ll get a sauce based on buffalo and ranch flavors for chicken, a mustardy one for burgers,  |
| TRUFF Hot Sauce Variety Pack | descriptive | — | TRUFF hot sauce, made with truffles, has been all the rage lately. This set of three bottles is packaged in a sleek box that makes a statement gift. |
| Tabasco Family of Flavors Gift Box | descriptive | — | Tabasco has a 150-year history , so it’s got a lot of fans. You get seven bottles of various varieties in this pack, including the Original Red Sauce and more unique flavors like Sweet & Spicy Sauce. |
| Swag Brewery Beer-Infused Hot Sauce Variety Pack | descriptive | — | Does your chile head also like beer? Chances are they might not have these beer-infused sauces yet. These are pretty mild and come in sriracha, garlic serrano, and roasted chipotle flavors. |
| Kumana Avocado Hot Sauce Variety Pack | descriptive | — | Inspired by Venezuelan guasacaca, Kumana hot sauce is made with avocados, herbs, bell peppers, and fruit for a complex flavor. This three-pack includes original, mango, and extra hot varieties, and is |
| Sriracha Hot Sauce Gift Set | descriptive | — | Sriracha has a cult following, and this set of four hot goodies would be perfect for a devotee. It includes classic sriracha, green sriracha, garlic sriracha, and super hot sriracha. |
| Nando’s Peri-Peri Extra Hot Sauce Lover’s Pack | descriptive | — | Nando’s is an international restaurant chain known for its chicken and peri-peri hot sauces full of citrus and spices. Your giftee can dip chicken into these medium, garlic, hot, and XX hot versions. |
| Season 16 Heat Pack | descriptive | — | The ever-popular YouTube series “Hot Ones” features a celebrity guest interview while they eat increasingly hot sauces. The sauces used on the show are available in three-packs so your giftee can recr |
| Adult Swim Rick and Morty Hot Sauce Challenge | descriptive | — | The Adult Swim show “Rick and Morty” has a dedicated fan base, and they would no doubt love this six-bottle show-themed hot sauce challenge set. |
| Blazing BBQ Box Sauce | descriptive | — | The line between hot sauce and barbecue sauce can be blurry, and that’s true for this hot barbecue sauce set. It includes a sweet and hot apple barbecue, chipotle hot sauce, wing sauce, and some dry r |
| The Fire Breather Broquet | descriptive | — | A chile head who wants to analyze and catalog their sauces would love this crate, which comes with a notebook for all their tasting notes. They’ll also get six bottles of hot sauce that’ll make them s |
| Women Sauce Maker Pack | descriptive | — | If your giftee is a woman, she might appreciate this hot sauce three-pack with brands made by women in a male-dominated market. It includes Hot n Saucy, Garlic N Peperoncini; Butterfly Bakery of Vermo |

## 5. The Condiment We Ranked Highest In Glen Powell's Smash Kitchen Line Is Perfectly Sweet And Spicy

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Hot Honey BBQ Sauce | positive | — | The Hot Honey BBQ absolutely wowed us compared to its American-style counterpart and took home the gold (while the medal for the worst condiment definitely went to Smash Kitchen's Classic Tomato Ketch |

## 6. Dr.Seuss' The Lorax - Original Songs from the Motion Picture (Habanero Orange Vinyl)

抽到 **0 筆**評語。

## 7. The must-have condiments we can’t live without

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Yucateo hot sauce | positive | — | This small but mighty hot sauce packs enough punch to give both Sriracha and Tabasco a run for their money. Less garlicky than the former and more chilli-flavoured than the latter, it is our condiment |
| Sriracha | positive | — | Sriracha has been one of the best spicy sauces for well over 10 years now. Today it’s available in 5 flavours and its beauty is really in its versatility: it is as at home on top of rice or pasta dish |
| Harissa | positive | — | Another chilli-based sauce that can well and truly transform a meal, the North African harissa is capable of supercharging all sorts of dishes – meat, fish and vegetables, even eggs and pasta – to mak |
| Tabasco | positive | — | The classic ingredient in a Blood Mary, prawn cocktail, and on oysters, Tabasco has a loyal fan base and its vinegary sweet hit is great as an ingredient. |
| Crispy chilli oil | positive | — | We love the Lao Gan Ma for use in noodle dishes or as a dip for dumplings. |

## 8. The 28 Best Hot Sauces on Amazon to Spice Up Your Life

**驗證沒過**：輸出不是合法 JSON（Expecting property name enclosed in double quotes: line 1 column 10874 (char 10873)）

抽到 **0 筆**評語。

## 9. Why The Best Condiment For Grilled Cheese Isn't Ketchup

抽到 **0 筆**評語。

## 10. Tabasco’s Other Treasures

抽到 **0 筆**評語。

## 11. Mountain Dew Baja Blast Hot Sauce Review: I’m Still Alive

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Mountain Dew Baja Blast Hot Sauce | mixed | — | It’s meant to be a fun gimmick more than a serious hot sauce, as evidenced by the fact that only 750 bottles are being produced and you can only get one by winning a contest — you can’t go to a store  |

## 12. A hot time at the home of Tabasco

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Original Red | descriptive | — | During the tour, guests are given dinky sample bottles of the complete range of Tabasco brand sauces – Original Red, Green Jalapeño, Chipotle, Buffalo Style, Habanero, Garlic Pepper, and Sweet & Spicy |
| Green Jalapeño | descriptive | — | During the tour, guests are given dinky sample bottles of the complete range of Tabasco brand sauces – Original Red, Green Jalapeño, Chipotle, Buffalo Style, Habanero, Garlic Pepper, and Sweet & Spicy |
| Chipotle | descriptive | — | During the tour, guests are given dinky sample bottles of the complete range of Tabasco brand sauces – Original Red, Green Jalapeño, Chipotle, Buffalo Style, Habanero, Garlic Pepper, and Sweet & Spicy |
| Buffalo Style | descriptive | — | During the tour, guests are given dinky sample bottles of the complete range of Tabasco brand sauces – Original Red, Green Jalapeño, Chipotle, Buffalo Style, Habanero, Garlic Pepper, and Sweet & Spicy |
| Habanero | descriptive | — | During the tour, guests are given dinky sample bottles of the complete range of Tabasco brand sauces – Original Red, Green Jalapeño, Chipotle, Buffalo Style, Habanero, Garlic Pepper, and Sweet & Spicy |
| Garlic Pepper | descriptive | — | During the tour, guests are given dinky sample bottles of the complete range of Tabasco brand sauces – Original Red, Green Jalapeño, Chipotle, Buffalo Style, Habanero, Garlic Pepper, and Sweet & Spicy |
| Sweet & Spicy | descriptive | — | During the tour, guests are given dinky sample bottles of the complete range of Tabasco brand sauces – Original Red, Green Jalapeño, Chipotle, Buffalo Style, Habanero, Garlic Pepper, and Sweet & Spicy |

## 13. Scotch Bonnet vs Habanero: Revealing 3 Key Differences in This Spicy Family

抽到 **0 筆**評語。

## 14. Spicy Ketchup | Jalapeño, Chipotle & Hot Ketchup | Hot Sauce Depot

抽到 **0 筆**評語。

## 15. Can’t Find Sriracha When Grocery Shopping? Blame the Weather.

抽到 **0 筆**評語。

## 16. The Best Condiments, Sauces, and Dressings of 2019

抽到 **0 筆**評語。

## 17. Why did Huy Fong, the beloved Sriracha brand, halt production again?

抽到 **0 筆**評語。

## 18. The Best Hot Sauce To Instantly Elevate Micheladas

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Valentina Mexican Hot Sauce | positive | — | Valentina Mexican Hot Sauce is the best hot sauce to use when crafting a michelada |

## 19. A Definitive Ranking of Popular Hot Sauces

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Louisiana Hot Sauce | mixed | — | You’re not getting anything too special. There’s nothing wrong with this sauce, per se, but compared to the others on this list, it’s just kind of boring. It has a medium heat level, but most of that  |
| Valentina | mixed | — | One thing I love about Valentina is the fact that, compared to many other hot sauces on the market, this one looks and feels thicker. It’s better for coating meats and veggies, and it doesn’t have the |
| Texas Pete | mixed | — | Here’s another one that tastes great but just can’t bring the level of heat we’re looking for: Texas Pete . This brand’s original hot sauce is the kind of stuff you would drizzle on every bite of a bu |
| Cholula | mixed | — | Yet again, we’re talking about a sauce that doesn’t bring enough heat. This time, it’s the Tex-Mex restaurant staple, Cholula . These types of mass-produced hot sauces tend to go light on the spice le |
| Taco Bell Fire Sauce | positive | — | Okay, okay, I know I might get some pushback from this one, but Taco Bell’s Fire Sauce, is, well, really good. Unlike their milder flavors (some of which are also delicious—looking at you, Verde Sauce |
| Tabasco | positive | — | Tabasco is a classic we all know and love. The original red pepper sauce is a winner for so many reasons. First of all, and most importantly, it’s actually spicy. It’s not so spicy that those with a s |
| Frank’s RedHot | positive | — | I know that not all fans of spice love Frank’s RedHot because it is quite mild. However, this hot sauce provides such a punch of flavor to anything you put on it that it has earned its distinguished p |
| Huy Fong Foods’ Sriracha | positive | — | Perhaps the most essential of all hot sauces, Huy Fong Foods Sriracha is an absolute fridge essential. I’m also in love with their Sambal Oelek, but the sriracha just seems to go on anything and every |
| Yellowbird Habanero Sauce | positive | — | One of the hottest peppers out there is the habanero, so it only makes sense that a habanero-based hot sauce would rank high on this list. Yellowbird’s Habanero Hot Sauce is everything I’ve ever dream |
| Fly By Jing Sichuan Chili Crisp | positive | — | Does chili crisp count as a hot sauce? For me, absolutely. It can be used in much the same way, even though this Fly By Jing’s Sichuan Chili Crisp adds not just flavor but also a lovely texture. It of |

## 20. Gringo Bandito Hot Sauce Review

| 抽到的醬 | stance | score_raw | 引文 |
|---|---|---|---|
| Gringo Bandito Green Sauce | positive | 4/5 | While they’re all delicious in their own unique way, our absolute favorite was the Gringo Bandito Green Sauce. |

