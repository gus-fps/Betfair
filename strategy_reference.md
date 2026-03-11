# Strategy Reference

> **Private — do not push to GitHub.**

All bots scan every 5 minutes, enter only within 90 minutes of kick-off, and log to their own CSV ledger. Stakes are set via `paper_stake` in `strategy_config.json` (currently £10).

---

## 1. BTTS Yes — `ghost_bot_BTTS_v2.py`

| Field | Value |
|---|---|
| Market | Both Teams to Score |
| Selection | Back **Yes** |
| Odds range | 1.81 – 2.60 |
| Ledger | `paper_trading_ledger_btts.csv` |

**Allowed leagues:**
- Brazilian Serie A
- Chinese Super League
- French Ligue 1
- Italian Serie A
- Italian Serie B
- Portuguese Segunda Liga
- South Korean K League 1
- Spanish Segunda Division
- Turkish Super League
- Uruguayan Primera Division

**Excluded teams** (substring match against match name):
Ajaccio, Alcorcon, Andorra, Andorra CF, Arouca, Bahia, Basaksehir, Besiktas, Botafogo, Burgos, Carrarese, Casa Pia, CD Castellon, Centro Atletico Fenix, Cerrito, Cerro Largo, Cittadella, Clermont, Cruzeiro MG, Cuiaba, Elche, Empoli, Espanyol, Fatih Karagumruk, Fiorentina, Fluminense, Fortaleza EC, Frosinone, Galatasaray, Gimcheon, Girona, Granada, Guangzhou City, Gwangju, Hatayspor, Henan, Incheon, Inter, Jeonbuk, Juventus, Lecce, Leganes, Leiria, Logrones, Mafra, Malaga, Malatyaspor, Mallorca, Man City, Napoli, Nice, Os Belenenses, Palmeiras, Penarol, Penafiel, Perugia, Pescara, Pordenone, Qingdao Jonoon, Reggiana, Reggina, Rennes, Santa Clara, Santos, Seongnam, Spezia, Sport Recife, Suwon Bluewings, Tenerife, Torino, Toulouse, Valladolid, Varzim, Wanderers (Uru)

---

## 2. BTTS No — `ghost_bot_BTTS_No.py`

| Field | Value |
|---|---|
| Market | Both Teams to Score |
| Selection | Back **No** |
| Odds range | 1.81 – 2.40 |
| Ledger | `paper_trading_ledger_btts_no.csv` |

**Allowed leagues:**
- English Championship
- Uruguayan Primera Division
- Uruguayan Segunda Division

**Excluded teams** (substring match against match name):
Albion FC, Bristol City, Colon FC, IA Sud America, Ipswich, Leicester, Liverpool Montevideo, Middlesbrough, Miramar Misiones, Oxford Utd, Portsmouth, Progreso, Reading, River Plate (Uru), Rocha FC, Southampton, Sud America, Sunderland, Tacuarembo, Torque, Villa Espanola

---

## 3. Draw HT — `ghost_bot_Draw_HT.py`

| Field | Value |
|---|---|
| Market | Half Time result |
| Selection | Back **The Draw** |
| Odds range | 1.81 – 3.00 |
| Ledger | `paper_trading_ledger_draw_ht.csv` |

**Allowed leagues:**
- Argentinian Primera B Nacional
- South Korean K League 1
- South Korean K League 2
- Uruguayan Segunda Division

**Excluded teams** (substring match against match name):
Aldosivi, Asan Mugunghwa, Bella Vista, Central Norte, Cerrito, Colon, Daejeon Citizen, Flandria, Guillermo Brown, IA Potencia, Instituto, La Luz FC, Miramar Misiones, Patronato, Racing de Cordoba, Rocha FC, San Telmo, Seongnam, Suwon FC, Temperley, Tigre, Villa Espanola, Villa Teresa

---

## 4. Over 1.5 HT — `ghost_bot_O1.5HT.py`

| Field | Value |
|---|---|
| Market | First Half Goals 1.5 |
| Selection | Back **Over 1.5 Goals** |
| Odds range | 1.61 – 5.00 |
| Ledger | `paper_trading_ledger_o15ht.csv` |

**Allowed leagues:**
- Brazilian Serie A
- Brazilian Serie B
- French Ligue 1
- German Bundesliga
- Italian Serie B
- Portuguese Segunda Liga

**Excluded teams** (substring match against match name):
ABC RN, Academica, Ajaccio, Amazonas FC, Amiens, Arminia Bielefeld, Athletic Club, Atletico Go, Atletico MG, Augsburg, Avai, AVS Futebol SAD, Bahia, Bari, Belenenses, Benevento, Botafogo, Brusque FC, Cagliari, Carrarese, Casa Pia, CD Trofense, Chapecoense, Chievo, Cittadella, Clermont, Como, Cosenza, Cova da Piedade, Criciuma, Cuiaba, EC Vitoria Salvador, Empoli, ESTAC Troyes, Farense, FC Koln, Feralpisalo, Feirense, Felgueiras, Ferroviaria, Flamengo, Fluminense, Fortuna Dusseldorf, Frosinone, Genoa, Goias, Greuther Furth, Guarani, Juve Stabia, Le Havre, Lecco, Leixoes, Lille, Livorno, Lyon, Mantova, Marseille, Montpellier, Monza, Nantes, Nice, Paris St-G, Penafiel, Perugia, Pescara, Ponte Preta, Portimonense, RB Leipzig, Reggiana, Reggina, Reims, Remo, Rennes, Rio Ave, Sampdoria, Sampaio Correa, Schalke 04, Spezia, Sport Recife, St Pauli, Strasbourg, Sudtirol, Tombense MG, Tondela, Toulouse, Trapani, Varzim, Vilafrancquense, Vilaverdense, Vitoria BA, Vizela, Volta Redonda

---

## 5. Lay The Draw — `ghost_bot_LTD_pre_live.py`

| Field | Value |
|---|---|
| Market | Match Odds |
| Selection | **Lay The Draw** |
| Lay odds range | 3.00 – 3.60 |
| Liability | Fixed £10 per bet |
| Ledger | `paper_trading_ledger_ltd.csv` |

> The lay stake varies per bet to keep the liability constant at £10. Formula: `lay_stake = 10 / (odds − 1)`. At odds 3.00 this is ~£5.00; at 3.60 it is ~£3.85. The `Stake` column in the ledger shows the actual lay stake, not the liability.

**Allowed leagues:**
- Argentinian Primera B Nacional
- Belgian Pro League
- Dutch Eredivisie
- English Championship
- English Premier League
- French Ligue 1
- German Bundesliga 2
- Japanese J League
- Uruguayan Segunda Division

**Excluded teams** (substring match against match name):
Almere City, Amiens, Angers, Arminia Bielefeld, Atenas, Birmingham, Brown de Adrogue, CA Atlanta, CA Rentistas, CA Villa Teresa, Club Brugge, Club Oriental de La Paz, Deportivo Moron, Deportivo Riestra, ESTAC Troyes, Estudiantes Rio Cuarto, Eupen, FC Utrecht, FCV Dender, Ferro Carril Oeste, Fulham, Gent, Gimnasia Mendoza, Heracles, Independiente Rivadavia, Ingolstadt, Jahn Regensburg, Kashima, Kfco Beerschot Wilrijk, Leeds, Lens, Liverpool, Luton, Man Utd, Miramar Misiones, Molenbeek, Monaco, Nice, Nottm Forest, Oud-Heverlee Leuven, Peterborough, QPR, Racing Club (Uru), Racing de Cordoba, RKC Waalwijk, Sapporo, Sendai, Shonan, Standard, Sunderland, Tosu, Tristan Suarez, Urawa, West Brom

---

## 6. Under 2.5 Goals 1H — `ghost_bot_U2.5_1H_15min.py`

| Field | Value |
|---|---|
| Market | Over/Under 2.5 Goals (full match) |
| Selection | Back **Under 2.5 Goals** pre-match, hedge in-play |
| Odds range (entry) | 1.81 – 2.40 |
| Ledger | `paper_trading_ledger_u25_1h.csv` |

**Allowed leagues:**
- Chilean Primera B
- Portuguese Primeira Liga

**Excluded teams** (substring match against match name):
Barnechea, Chaves, Estoril Praia, Famalicao, Guimaraes, Qingdao Jonoon, Shenyang Urban FC, Vizela, Yunnan Yukun

### Position management

This bot has two routines running every cycle, unlike the others which only settle after the market closes.

**Routine A — Hedge (in-play)**
- Once the match goes in-play, the bot records the kickoff odds for the `Kickoff_Odds` column.
- At **15 minutes elapsed**, it lays "Under 2.5 Goals" to lock in an equal profit on both outcomes regardless of the final result.
- Hedge stake formula: `hedge_stake = back_stake × back_odds / current_lay_odds`
- Locked profit formula: `locked_profit = back_stake × (back_odds − lay_odds) / lay_odds`
- If the lay odds at 15 min are better than the back odds, the locked profit will be positive on both sides. If they've shortened, it will be a small loss regardless of outcome.
- If no lay price is available at 15 min, it retries on the next 5-minute cycle.
- **Fallback:** if the bot was offline at the 15-minute mark and the market closes before it can hedge, it settles the bet as a normal back bet (WIN/LOSS). The ledger marks these with `(unhedged)` in the console output.

**Routine B — New bets (pre-match)**
- Standard pre-match scan within 90 minutes of kick-off.
- Stores the scheduled `Kickoff` datetime in the ledger — this is what Routine A uses to calculate when 15 minutes have elapsed in-play.

---

## 7. Over 1.5 Goals Final — `ghost_bot_O15_final.py`

| Field | Value |
|---|---|
| Market | Over/Under 1.5 Goals (full match) |
| Selection | Back **Over 1.5 Goals** |
| Odds range | 1.61 – 2.20 |
| Entry timing | In-play, approximately 70–75 game minutes |
| Score condition | 0-1 or 1-0 at time of entry |
| Ledger | `paper_trading_ledger_o15f.csv` |

**Allowed leagues:**
- Chinese Super League
- French Ligue 1
- German Bundesliga
- German Bundesliga 2
- Greek Super League

**Excluded teams** (substring match against match name):
Asteras Tripolis, Ionikos, Metz, Qingdao Jonoon

### How score and timing are detected

The Betfair REST API does not expose the live score or exact game minute. The bot uses two indirect methods:

**Game minute:** Estimated from clock time since the scheduled kickoff. Halftime adds ~15 minutes of clock time that doesn't count as game time, so:
- 70 game min ≈ 85 clock min since kickoff
- 75 game min ≈ 90 clock min since kickoff

The bot targets 83–93 clock minutes (≈ game minutes 68–78) to cover the window with a small buffer for late kickoffs and stoppage time.

**Score (0-1 or 1-0):** Verified indirectly without an external score feed:
1. **"Under 1.5 Goals" runner status = `ACTIVE`** — confirms at most 1 goal has been scored. If 2+ goals had occurred this runner would be `LOSER` and the market settled.
2. **Odds on "Over 1.5 Goals" in range 1.61–2.20** — at 70+ minutes with 0 goals scored, the market would price this at ~3.5–6.0+. Odds in this range strongly imply exactly 1 goal has been scored.

Together these two checks reliably select games that are 0-1 or 1-0 at the entry time.

**Scan frequency:** Adaptive — 1 minute when any allowed market is in the ~68–98 clock minute range (approaching or inside the entry window); 5 minutes otherwise. This keeps API calls low outside the second half.

---

## 8. Over 2.5 Goals UY+KR — `ghost_bot_O2.5_UY_KR.py`

| Field | Value |
|---|---|
| Market | Over/Under 2.5 Goals (full match) |
| Selection | Back **Over 2.5 Goals** |
| Odds range | 1.81 – 3.04 |
| Ledger | `paper_trading_ledger_o25.csv` |

**Allowed leagues:**
- South Korean K League 1
- Uruguayan Primera Division
- Uruguayan Segunda Division

**Excluded teams** (substring match against match name):
Atenas, Bella Vista, Boston River, CA Bella Vista, CA Rentistas, Cerro Largo FC, Club Oriental de La Paz, Colon FC, CSyD Cooper, Daegu FC, Daejeon Citizen, Danubio, FC Seoul, Gwangju FC, IA Potencia, IA Sud America, Incheon Utd, Jeonbuk Motors, Juventud De Las Piedras, La Luz FC, Penarol, Plaza Colonia, Pohang Steelers, Racing Club (Uru), Rampla Juniors, Sangju Sangmu, Suwon Bluewings, Villa Espanola, Wanderers (Uru)

---

## 9. Over 2.5 Goals ARG — `ghost_bot_O2.5_ARG.py`

| Field | Value |
|---|---|
| Market | Over/Under 2.5 Goals (full match) |
| Selection | Back **Over 2.5 Goals** |
| Odds range | 1.81 – 2.20 |
| Ledger | `paper_trading_ledger_o25_arg.csv` |

**Allowed leagues:**
- Argentinian Primera Division (covers Liga Profesional + Copa de la Liga Profesional)
- Argentinian Primera Nacional (second tier)

**Excluded teams** (substring match against match name):
Aldosivi, Atletico Mitre, Belgrano, CD MAIPU, Central Cordoba, Defensa y Justicia, Estudiantes, Ferro Carril, Gimnasia, Godoy Cruz, Lanus, Newells, Racing Club, River Plate, Rosario Central, San Lorenzo, San Martin, San Telmo, SM de Tucuman, Union Santa Fe

> **Substring coverage notes:** "Ferro Carril" catches all Ferro Carril Oeste name variants. "Gimnasia" catches both Gimnasia La Plata and Gimnasia Mendoza. "River Plate" catches both River Plate and CA River Plate BA. "San Martin" catches San Martin Tucuman and San Martin de Tucuman. "SM de Tucuman" is included separately as Betfair sometimes uses this abbreviation. "Newells" catches Newells Old Boys.

---

## 10. Lay Home Team 1st Half — `ghost_bot_LTH_1H.py`

| Field | Value |
|---|---|
| Market | Match Odds (1X2) |
| Selection | **Lay the Home Team** |
| Pre-match home odds filter | 1.38 – 2.15 (home team must be favourite) |
| In-play lay odds range | 2.50 – 5.09 |
| Entry timing | In-play, from the **38th minute** to end of 1st half (including stoppage time) |
| Score at entry | 0-0, 0-1, 1-1, or 1-2 (implicit — see note below) |
| Exit | Hedge (back home team) after **15 minutes** of exposure |
| Ledger | `paper_trading_ledger_lth.csv` |

**Allowed leagues:**
- Argentina Liga Profesional (covers Copa de la Liga Profesional)
- Argentinian Primera Nacional (second tier)
- Belgian First Division A
- Brazilian Serie B
- Dutch Eredivisie
- English Championship
- English Premier League
- French Ligue 1
- German Bundesliga 2
- Greek Super League
- Japanese J. League (top flight)
- Japanese J League 2 *(ID pending — run `league_search.py` with query `'Japan'`)*
- Portuguese Primeira Liga
- South Korean K League 1
- South Korean K League 2
- Spanish Segunda Division
- Uruguayan Segunda Division

**Excluded teams** (substring match against match name):
Albacete, Ansan Greeners, Argentinos Juniors, Atl Tucuman, Botafogo, Bournemouth, Bristol City, CD Castellon, Charleroi, CSA, Defensores Unidos, EC Vitoria Salvador, Estudiantes, FC Anyang, FC Utrecht, Fortuna Sittard, Huracan, Kofu, Kortrijk, Levante, Mito, PAOK, Reims, Southampton, Sparta Rotterdam, Sunderland, Talleres, Torreense, Zulte-Waregem

### How the bot works

**Three routines per cycle:**

**Routine A — Hedge / settle pending bets**
- For each `PENDING_HEDGE` bet, checks how long it has been open.
- If **15+ minutes** have elapsed and the market is open: backs the home team at current market price to lock in the position.
  - `hedge_stake = lay_stake × lay_odds / current_back_odds`
  - `locked_profit = lay_stake − hedge_stake`
  - Positive if odds drifted (home team less likely to win than at entry). Negative if odds shortened.
- If the market **closes before the hedge is placed** (rare): settles as a standard lay (WIN if home didn't win; LOSS if home won).
- If no back price is available at the 15-min mark: retries on the next 5-minute cycle.

**Routine B — Pre-match approval scan**
- Within 90 minutes of kickoff, records any match where the home team's back odds are in the **1.38–2.15** range.
- These approved markets are held in memory. If the bot restarts, in-play markets without a pre-match record are safely skipped.

**Routine C — In-play entry scan (part of Routine B cycle)**
- For approved markets that are now in-play within the entry window (**38–52 clock minutes** since kickoff), checks if the home team's lay odds are in **2.50–5.09**.
- Entry is blocked during market suspensions (goals, halftime break), as Betfair sets `status = SUSPENDED` at those moments.

> **Score filter note:** No explicit score feed is needed. The lay odds range acts as an implicit score filter. If the home team (pre-match favourite at 1.38–2.15) is winning 1-0 or 2-0 at the 38th minute, their in-play lay odds will have shortened to ~1.2–1.8 — below our 2.50 minimum, so no bet is placed. If they are losing badly (0-2, 0-3), odds exceed 5.09 — also excluded. What remains in the 2.50–5.09 window at this stage corresponds precisely to the four target scorelines: **0-0, 0-1, 1-1, and 1-2**.

---

## 11. BTTS Freebet 2H — `ghost_bot_BTTS_FB_2H.py`

| Field | Value |
|---|---|
| Market | Both Teams to Score |
| Selection | Back **Yes** |
| Entry odds range | 8.20 – 11.00 |
| Entry timing | In-play, 2nd half, game minutes **55–70** (clock min 70–85) |
| Score at entry | 0-0 (implicit — see note below) |
| Exit | Freebet lay once a goal drops odds below entry back odds |
| Ledger | `paper_trading_ledger_btts_fb.csv` |

**Allowed leagues:**
- Belgian First Division A
- Brazilian Serie A
- English Championship
- English Premier League
- French Ligue 1
- Italian Serie A
- Portuguese Primeira Liga
- Turkish Super League
- US Major League Soccer

**Excluded teams** (substring match against match name):
Antalyaspor, Antwerp, Atletico Go, Auxerre, Basaksehir, Besiktas, Bologna, Braga, Brentford, Burnley, Casa Pia, Charleroi, Cruzeiro MG, DC Utd, Famalicao, Fiorentina, Flamengo, Fortuna Sittard, Fulham, Hatayspor, Heracles, Konyaspor, Lille, Lorient, Maritimo, Millwall, New England, Norwich, Oud-Heverlee Leuven, Philadelphia, Preston, RKC Waalwijk, Santa Clara, Santos, Sao Paulo, SE Palmeiras, Southampton, Sport Recife, Stoke, Tosu, Watford

### How the bot works

**Entry:** Back BTTS Yes in the 55–70 game minute range at odds 8.20–11.00. The odds range implicitly confirms a 0-0 score — if one team had already scored, BTTS Yes would be priced ~2.5–4.5, well outside this range.

**Freebet exit (Routine A):** Every cycle, checks if BTTS Yes lay odds have dropped below the original back odds (i.e., a goal was scored, making BTTS Yes more likely):
- `freebet_stake = back_stake × (back_odds − 1) / (lay_odds − 1)`
- This creates a risk-free position:
  - **If BTTS wins** (both teams score): back wins, lay loses → **net = 0 (break even)**
  - **If BTTS fails** (not both score): lay wins, back loses → **net profit = back_stake × (back_odds − lay_odds) / (lay_odds − 1)**
- Freebet is only placed when lay_odds < back_odds (guaranteed worst-case break-even).
- If the market closes before a goal is scored (game ends 0-0): **LOSS = −back_stake**.

**Result states in ledger:**
- `PENDING_FREEBET` → watching for goal
- `FREEBET_PLACED` → freebet lay done, awaiting final settlement
- `WIN` → BTTS failed after freebet (profit locked)
- `BREAK_EVEN` → BTTS won after freebet (net zero)
- `LOSS` → game ended 0-0, no freebet placed
- `WIN_UNHEDGED` → both teams scored before freebet could be placed (rare)
