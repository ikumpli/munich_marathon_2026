"""Personal final-weekend checklist, explicitly dated and separate from activity actuals."""
from html import escape

PRE_MARATHON_CSS = """
.pre-plan { --pre-mint:#a7f3d0; --pre-amber:#fcd34d; color:#e2e8f0; }
.pre-plan h2, .pre-plan h3, .pre-plan h4 { margin:0; font-weight:700; }
.pre-plan p { margin:0; color:#b7c6d9; line-height:1.65; }
.pre-hero { position:relative; padding:2rem; border:1px solid #335563; border-radius:20px; background:radial-gradient(ellipse at 100% 0%,#1e4850 0,transparent 65%),#122332; overflow:hidden; }
.pre-hero::after { content:'09:20'; position:absolute; right:1.4rem; bottom:-1.4rem; font-size:7rem; font-weight:800; color:#a7f3d0; opacity:.045; pointer-events:none; }
.pre-eyebrow { color:var(--pre-mint); font-size:.7rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
.pre-hero h2 { margin:.7rem 0; font-size:clamp(1.8rem,4vw,2.6rem); letter-spacing:-.04em; color:#f8fafc; }
.pre-hero p { max-width:650px; }
.pre-chips { display:flex; gap:.65rem; flex-wrap:wrap; margin-top:1.3rem; }
.pre-chip { border:1px solid #42636d; background:#122635; padding:.45rem .75rem; border-radius:999px; font-size:.76rem; color:#d5ebe4; }
.pre-context { margin:1.2rem 0; padding:1rem 1.2rem; border-left:3px solid var(--pre-amber); border-radius:0 12px 12px 0; background:#242a32; font-size:.84rem; line-height:1.65; color:#e3d7b7; }
.pre-day-grid { display:grid; grid-template-columns:1fr 1fr; gap:1.1rem; }
.pre-day { border:1px solid #334155; border-radius:18px; overflow:hidden; background:#111e2e; }
.pre-day-head { display:flex; align-items:center; gap:1rem; padding:1.35rem 1.4rem; border-bottom:1px solid #334155; background:#192738; }
.pre-day-number { font-size:2.4rem; font-weight:800; letter-spacing:-.05em; color:var(--pre-amber); line-height:1; }
.pre-day:nth-child(2) .pre-day-number { color:var(--pre-mint); }
.pre-day-head h3 { font-size:1.05rem; }
.pre-day-sub { margin-top:.25rem; font-size:.77rem; color:#a9b9cd; }
.pre-day-tag { margin-left:auto; color:#cbd5e1; font-size:.67rem; text-transform:uppercase; border:1px solid #475569; border-radius:999px; padding:.3rem .55rem; }
.pre-events { padding:.4rem 1.4rem 1rem; }
.pre-event { display:grid; grid-template-columns:65px 1fr; column-gap:.8rem; padding:1rem 0; border-bottom:1px solid #263549; }
.pre-event:last-child { border:0; }
.pre-event time { font-size:.75rem; color:#94a3b8; padding-top:.15rem; font-variant-numeric:tabular-nums; }
.pre-event h4 { font-size:.88rem; color:#f1f5f9; margin-bottom:.25rem; line-height:1.4; }
.pre-event p { font-size:.8rem; }
.pre-event.accent time { color:var(--pre-amber); font-weight:700; }
.pre-event.accent h4 { color:#fde68a; }
.pre-day-foot { margin:0 1.4rem 1.3rem; padding:.8rem 1rem; border:1px solid #36515b; border-radius:12px; background:#172d35; font-size:.78rem; line-height:1.6; color:#c9e4dc; }
.pre-section-title { margin:1.7rem 0 .9rem !important; font-size:1.05rem; }
.pre-rule-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; }
.pre-rule { padding:1.2rem; background:#142132; border:1px solid #334155; border-radius:16px; }
.pre-rule-label { font-size:.66rem; letter-spacing:.1em; text-transform:uppercase; color:var(--pre-mint); }
.pre-rule h3 { margin:.5rem 0; font-size:1.2rem; }
.pre-rule p, .pre-rule li { font-size:.8rem; color:#b7c6d9; line-height:1.65; }
.pre-rule ul { padding-left:1.15rem; margin:.6rem 0 0; }
.pre-morning { margin-top:1.4rem; border:1px solid #3b5968; border-radius:18px; padding:1.4rem; background:#122735; }
.pre-morning-head { display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-bottom:1.1rem; }
.pre-morning h3 { font-size:1.15rem; }
.pre-morning-head span { color:var(--pre-mint); font-size:.8rem; }
.pre-steps { display:grid; grid-template-columns:repeat(5,1fr); gap:.8rem; }
.pre-step { padding:.85rem .85rem 1rem; border:1px solid #345260; border-radius:12px; background:#142e3a; }
.pre-step time { display:block; color:var(--pre-mint); font-size:1.25rem; font-weight:800; margin-bottom:.35rem; font-variant-numeric:tabular-nums; }
.pre-step strong { display:block; font-size:.8rem; margin-bottom:.35rem; }
.pre-step p { font-size:.76rem; }
.pre-lower { display:grid; grid-template-columns:1.15fr 1fr; gap:1rem; margin-top:1.3rem; }
.pre-panel { background:#142132; border:1px solid #334155; border-radius:16px; padding:1.3rem; }
.pre-panel h3 { font-size:1rem; margin-bottom:.65rem; }
.pre-panel p { font-size:.81rem; }
.pre-pack-top { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.pre-pack-count { font-size:.74rem; color:var(--pre-mint); }
.pre-check-grid { display:grid; grid-template-columns:1fr 1fr; gap:.5rem .8rem; margin-top:.9rem; }
.pre-check { display:flex; gap:.55rem; align-items:flex-start; font-size:.78rem; color:#cbd5e1; padding:.5rem .3rem; cursor:pointer; line-height:1.4; }
.pre-check input { width:17px; height:17px; flex-shrink:0; margin-top:1px; accent-color:#6ee7b7; }
.pre-check:has(input:checked) span { color:#87a394; text-decoration:line-through; }
.pre-progress { height:4px; background:#334155; border-radius:10px; margin-top:.7rem; overflow:hidden; }
.pre-progress > span { display:block; height:100%; background:#6ee7b7; transition:width .2s; width:0; }
.pre-reset { border:0; background:none; color:#94a3b8; font-size:.75rem; text-decoration:underline; padding:0; margin-top:.75rem; }
.pre-reset:focus-visible, .pre-check input:focus-visible { outline:2px solid #a7f3d0; outline-offset:3px; }
.pre-sources { margin-top:1.2rem; padding:.9rem 1.1rem; border:1px solid #334155; border-radius:12px; font-size:.78rem; color:#94a3b8; }
.pre-sources summary { font-size:.78rem; }
.pre-sources ul { padding-left:1.2rem; margin:.7rem 0 0; line-height:1.9; }
@media(max-width:900px) { .pre-rule-grid { grid-template-columns:1fr; } .pre-steps { grid-template-columns:repeat(3,1fr); } }
@media(max-width:600px) { .pre-hero { padding:1.3rem; } .pre-day-grid,.pre-lower { grid-template-columns:1fr; } .pre-steps { grid-template-columns:1fr; } .pre-step { display:grid; grid-template-columns:65px 1fr; gap:0 .6rem; } .pre-step time { grid-row:span 2; font-size:1.1rem; } .pre-day-tag { display:none; } .pre-morning-head { align-items:flex-start; flex-direction:column; gap:.3rem; } .pre-check-grid { grid-template-columns:1fr; } .pre-hero::after { font-size:5rem; } }
"""

PRE_MARATHON_JS = """
(function() {
  var root = document.getElementById('pre-marathon-plan');
  if (!root) return;
  var boxes = Array.from(root.querySelectorAll('[data-pre-pack]'));
  var key = 'munich-marathon-2026-pre-pack-v1';
  var stored = {};
  try { stored = JSON.parse(localStorage.getItem(key) || '{}') || {}; } catch (e) {}
  boxes.forEach(function(box) { box.checked = stored[box.dataset.prePack] === true; });
  function update(save) {
    var done = boxes.filter(function(box) { return box.checked; }).length;
    root.querySelector('[data-pre-count]').textContent = done + ' / ' + boxes.length + ' ready';
    root.querySelector('[data-pre-progress]').style.width = (done / boxes.length * 100) + '%';
    if (save) {
      var value = {};
      boxes.forEach(function(box) { value[box.dataset.prePack] = box.checked; });
      try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
    }
  }
  boxes.forEach(function(box) { box.addEventListener('change', function() { update(true); }); });
  root.querySelector('[data-pre-reset]').addEventListener('click', function() {
    boxes.forEach(function(box) { box.checked = false; }); update(true);
  });
  update(false);
  function openPre() {
    var button = document.getElementById('pre-marathon-tab');
    if (button && window.bootstrap && window.bootstrap.Tab) window.bootstrap.Tab.getOrCreateInstance(button).show();
  }
  if (location.hash === '#tab-pre-marathon') openPre();
  window.addEventListener('hashchange', function() { if (location.hash === '#tab-pre-marathon') openPre(); });
})();
"""


def _day(number, name, subtitle, tag, events, foot):
    entries = ''.join(
        f'<div class="pre-event{" accent" if accent else ""}">'
        f'<time>{escape(time)}</time><div><h4>{escape(title)}</h4>'
        f'<p>{description}</p></div></div>'
        for time, title, description, accent in events)
    return f'''<article class="pre-day" aria-label="{escape(name)}  {number} October">
      <header class="pre-day-head"><div class="pre-day-number">{number}</div>
      <div><h3>{escape(name)}</h3><div class="pre-day-sub">{escape(subtitle)}</div></div>
      <span class="pre-day-tag">{escape(tag)}</span></header>
      <div class="pre-events">{entries}</div><div class="pre-day-foot">{foot}</div></article>'''


def pre_marathon_html():
    friday = _day('09', 'Friday', 'Top up your fuel. Keep the day gentle.', '2 days to go', [
        ('Lunch', 'Rice bowl, familiar protein', 'A generous serving of white rice with a modest portion of chicken, eggs or your usual tofu, plus a little cooked veg. Add bread if you want more carbs.', False),
        ('15:30', 'An easy carbohydrate snack', 'A bagel or toast with jam, plus a banana. Use foods you already tolerate; no new supplements.', False),
        ('Optional', 'A very easy shakeout, or rest', 'Only if throat symptoms have settled and energy feels normal: <strong>15–20 min, maximum 3 km</strong>, conversational throughout. No strides or fast finish. Rest is equally fine; do not add this if you already jogged today.', False),
        ('17:30', 'Dinner before collection', 'White pasta with tomato sauce and a modest portion of familiar protein. A bread roll alongside is fine. If dinner is later, take a snack for the trip.', False),
        ('18:30', 'Collect bib 12283 + your shirt', '<strong>Olympiahalle, Olympiapark. Closes at 19:00.</strong> Bring photo ID and your QR code; leave a little arrival buffer. Check block D / 09:20, your chip and your shirt voucher or purchase.', True),
        ('20:00', 'Small snack if hungry', 'Familiar cereal, rice pudding if dairy suits you, or toast with honey. Sip normally; skip alcohol tonight.', False),
        ('22:30', 'Lights out → about 07:00', 'Aim for <strong>8–9 hours of sleep</strong>, allowing time to fall asleep. Keep your usual relaxing routine and avoid late caffeine.', False),
    ], 'Today is about recovery. If a jog brings back fatigue or symptoms, stop and check how you feel over the next 24 hours before deciding about Sunday.')
    saturday = _day('10', 'Saturday', 'Familiar food, quiet legs, everything packed.', '1 day to go', [
        ('08:00', 'Carb-rich breakfast', 'Bagels or white toast with jam/honey and a banana; cereal if that is your normal breakfast. Keep butter, avocado and other fatty extras modest.', False),
        ('10:30', 'Snack, then a short walk', 'Pretzels, a banana, or bread with jam. A small glass of juice is an option only if it agrees with your stomach. Walk gently for 10–15 min; no long sightseeing day.', False),
        ('12:30', 'Make lunch a proper meal', 'White rice or pasta, a modest portion of familiar protein and some cooked vegetables. For a portion guide, <strong>100–125 g dry rice/pasta</strong> is a generous base; adjust to your appetite.', False),
        ('15:30', 'Top up between meals', 'Bagel with jam, crackers, or a familiar rice pudding. Spread food through the day so dinner does not have to do all the work.', False),
        ('18:00', 'An early, comfortable dinner', 'Pasta with tomato sauce or rice, plus bread and a little familiar protein. Keep it low in fat and spice; limit large salads, beans and bran if they upset your gut.', False),
        ('19:30', 'Pack, charge, set two alarms', 'Pin the bib to your familiar top, fill in emergency contacts, label the Runner’s Bag and count your gels. Charge watch, phone and any permitted headphones.', True),
        ('20:00', 'Small final snack if wanted', 'Toast with jam, cereal or a familiar dessert. Nothing enormous, and no need to eat through discomfort.', False),
        ('21:00', 'Wind down → 21:30 lights out', 'Plan to wake at <strong>06:00</strong>, giving about 8½ hours in bed. If you need more time to fall asleep, wind down earlier. A restless night does not automatically undo your preparation.', False),
    ], '<strong>Rest from running.</strong> A few minutes of familiar gentle mobility is enough. Skip the Coffee Run, hard stretching, heavy strength, deep massage and jumping sports.')
    checks = [
        ('bib', 'Bib + safety pins; contacts filled in'),
        ('kit', 'Familiar shoes, socks and running kit'),
        ('gels', 'Familiar gels counted + one spare'),
        ('bag', 'Runner’s Bag labelled 12283'),
        ('clothes', 'Dry clothes + warm layer for afterwards'),
        ('devices', 'Watch / phone charged; alarms set'),
        ('breakfast', 'Breakfast ready for 06:20'),
        ('travel', 'Journey checked + meeting point agreed'),
    ]
    checklist = ''.join(f'<label class="pre-check"><input type="checkbox" data-pre-pack="{key}"><span>{escape(label)}</span></label>' for key, label in checks)
    return '''<section class="pre-plan" id="pre-marathon-plan" aria-labelledby="pre-title">
      <header class="pre-hero"><div class="pre-eyebrow">Your final weekend · 9–11 October 2026</div>
        <h2 id="pre-title">Arrive rested. Start comfortable.</h2>
        <p>A practical plan for food, sleep and the small things that make Sunday calmer. Follow the parts of today still ahead; there is no need to catch up on meals or running.</p>
        <div class="pre-chips"><span class="pre-chip">Sunday 09:20 · Block D</span><span class="pre-chip">Bib 12283</span><span class="pre-chip">8–9 hours sleep</span><span class="pre-chip">Saturday: rest</span></div>
      </header>
      <div class="pre-context"><strong>Your update · 9 October.</strong> You report only 4 km on Wednesday after a sore throat and low energy, no fever, and feeling healthy today. This weekend guidance supersedes the earlier Friday/Saturday advice. A comfortable short jog does not establish readiness for a marathon. If illness or unusual fatigue returns, reassess starting and get medical advice; fever, chest pain, unusual breathlessness or palpitations mean do not race.</div>
      <div class="pre-day-grid">''' + friday + saturday + '''</div>
      <h3 class="pre-section-title">Three things to keep simple</h3>
      <div class="pre-rule-grid">
        <article class="pre-rule"><div class="pre-rule-label">01 · Food & fluids</div><h3>Carbs through the day</h3><p>Use three carb-rich meals plus 2–3 familiar snacks. Rice, pasta, bread, bagels, cereal and bananas make this easier. Portions above are examples, not a calculated diet; keep eating comfortable.</p><ul><li>Keep some protein in meals.</li><li>Choose lower-fibre versions if they suit you.</li><li>Drink to thirst; do not force litres of water or new salt supplements.</li></ul></article>
        <article class="pre-rule"><div class="pre-rule-label">02 · Sleep</div><h3>Give yourself 8–9 hours</h3><p>Keep Friday night quiet and move Saturday’s bedtime a little earlier for the 06:00 wake-up. Allow extra time in bed if you need it to fall asleep.</p><ul><li>Cool, dark room; normal bedtime routine.</li><li>If needed, a 20–30 min nap early afternoon.</li><li>No new sleep aids or unfamiliar caffeine strategy.</li></ul></article>
        <article class="pre-rule"><div class="pre-rule-label">03 · Movement</div><h3>5 minutes is plenty</h3><p>For Friday or Saturday, one gentle round of familiar movements is optional. Stop well before fatigue; skip anything that aggravates your previous injury.</p><ul><li>8 ankle circles each direction, each side.</li><li>6–8 small, controlled leg swings each side, holding support.</li><li>30–60 sec of easy marching; relaxed walking.</li><li>No forceful or prolonged stretching, new drills or strength session.</li></ul></article>
      </div>
      <section class="pre-morning" aria-labelledby="pre-sunday-title"><div class="pre-morning-head"><h3 id="pre-sunday-title">Sunday morning, already decided.</h3><span>11 October · Munich time</span></div>
      <div class="pre-steps">
        <div class="pre-step"><time>06:00</time><strong>Wake + check how you feel</strong><p>Energy and breathing should feel normal. If you feel ill, do not start.</p></div>
        <div class="pre-step"><time>06:20</time><strong>Your familiar breakfast</strong><p>Bagels/toast with jam or honey + a banana. Use the portion you know sits well. Normal coffee only if familiar.</p></div>
        <div class="pre-step"><time>08:00</time><strong>Arrive at Olympiapark</strong><p>Aim for 08:00–08:15. Bag drop at Olympiahalle opens at 08:00; leave time for toilets.</p></div>
        <div class="pre-step"><time>09:05</time><strong>Be in block D</strong><p>Follow D/E assembly signs. Keep warm, walk gently and use a few familiar ankle movements; no workout needed.</p></div>
        <div class="pre-step"><time>09:20</time><strong>Start at comfortable effort</strong><p>Ease into the opening kilometres. After this week’s illness, make finishing well the priority and let go of the time goal.</p></div>
      </div></section>
      <div class="pre-lower"><section class="pre-panel"><h3>Fuel early. Keep it familiar.</h3><p>If <strong>25 g gels every 30 min</strong> are a pattern you have tolerated, an example is <strong>09:40, 10:10, 10:40</strong>, then every 30 min while running. This supplies roughly 50 g/hour over a longer race; count drink carbs too. Check your gel labels and take water as directed. This is an example, not a new intake to test on race day.</p><p style="margin-top:.65rem">Course gels begin at <strong>km 26.5</strong>, so carry your own early supply. For roughly 4½ hours, that example uses 9 gels plus a spare; carry more if you expect longer. No late push to recover a time target.</p></section>
      <section class="pre-panel"><div class="pre-pack-top"><h3 style="margin:0">Saturday’s packing check</h3><span class="pre-pack-count" data-pre-count aria-live="polite">0 / 8 ready</span></div><div class="pre-progress" aria-hidden="true"><span data-pre-progress></span></div><div class="pre-check-grid">''' + checklist + '''</div><button class="pre-reset" type="button" data-pre-reset>Reset checklist</button></section></div>
      <details class="pre-sources"><summary>Food amounts, source notes & practical details</summary>
        <p style="font-size:.78rem;margin-top:.65rem">Formal carbohydrate-loading protocols commonly use 10–12 g/kg/day for 36–48 hours. At your previously recorded 74 kg, that would be about 740–890 g/day: a substantial amount. The meal ideas here are not calculated to meet that protocol. Use familiar carbohydrate foods regularly, and do not force an unfamiliar volume or new products into this final weekend.</p>
        <p style="font-size:.78rem;margin-top:.65rem">This is a practical coaching plan dated 9 October, based on your report rather than a diagnosis or medical clearance. The brief mobility routine is a comfort suggestion, not a proven injury-prevention or performance intervention. Your bib/confirmation covers MVV zones M–6 on Sunday. Check MVG for your route. Arrange a post-race meeting flag A–E at Hans-Jochen-Vogel-Platz.</p>
        <ul><li><a href="https://marathonmuenchen.org/wp-content/uploads/2026/10/mm26-runners-guide-en-screen.pdf" target="_blank" rel="noopener">Munich runner’s guide: collection, start blocks, bag drop and meeting points</a></li>
        <li><a href="https://www.londonmarathonevents.co.uk/london-marathon/medical-advice" target="_blank" rel="noopener">London Marathon medical guidance: illness, carbohydrate topping up and hydration</a></li>
        <li><a href="https://worldathletics.org/download/download?filename=6babe10a-9969-407e-b0cd-f7d96df50f51.pdf&amp;urlslug=Contemporary+Nutrition+Strategies+to+Optimize+Performance+in+Distance+Runners+and+Race+Walkers" target="_blank" rel="noopener">World Athletics: carbohydrate loading and pre-race meals</a></li>
        <li><a href="https://bjsm.bmj.com/content/55/7/356" target="_blank" rel="noopener">Athlete sleep consensus: individual needs, sleep opportunity and naps</a></li>
        <li><a href="https://www.casem-acmse.org/wp-content/uploads/2024/11/1066.full_.pdf" target="_blank" rel="noopener">IOC guidance: gradual return after respiratory illness and monitoring for 24 hours</a></li>
        <li><a href="https://www.ausport.gov.au/ais/nutrition/supplements/group_a/sports-foods2/sports-gels/how-and-when-do-i-use-it" target="_blank" rel="noopener">AIS: carbohydrate during exercise and practicing gut tolerance</a></li></ul>
      </details>
    </section>'''
