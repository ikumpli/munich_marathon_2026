"""Dated coaching review, kept separate from automatically refreshed activity data."""
from datetime import date
from html import escape
import pandas as pd

REVIEW_DATE = date(2026, 9, 22)
RACE_DISTANCE_KM = 42.195
REVIEW_NOTE = (
    'Updated 22 September after the 20 km run and your reported physio okay. '
    'Three easy runs this week, three next week, then two short runs before race day. '
    'Use conversational effort (2–3/10); roughly 6:15–6:45/km or slower. '
    'An approximate 145–150 bpm is a useful easy-run reference, not a tested zone or a target to chase. '
    'Distances are upper limits: shorten or skip for fatigue. If the injury pain returns, '
    'increases, changes your stride or leaves next-morning swelling/stiffness, stop running '
    'and follow up with your physio. No missed-distance catch-up or new hard sessions.'
)

FINAL_WEEKS = [
    (16, 'Sep 21', 29, 18,
     'Mon: Rest; participation review before entry-change deadline · '
     'Tue: Easy 5k, conversational; shorten if still tired from Sunday · '
     'Wed: Rest or gentle swim; familiar physio exercises · '
     'Thu: Easy 6k; practice relaxed opening effort, no fast finish · '
     'Fri: Rest; familiar light physio exercises · '
     'Sat: Rest or easy walk · '
     'Sun: Long 18k maximum OR 110 min, whichever first; easy throughout; rehearse breakfast and fuel; shorten to 12–14 km if recovery is incomplete',
     'Consolidate'),
    (17, 'Sep 28', 20, 10,
     'Mon: Rest or gentle swim if recovered · '
     'Tue: Easy 5k; relaxed and conversational · '
     'Wed: Rest; light familiar physio exercises · '
     'Thu: Easy 5k; no pace test · '
     'Fri: Rest · '
     'Sat: Rest or easy walk · '
     'Sun: Long 10k easy maximum; finish fresh', 'Taper'),
    (18, 'Oct 5', 49.195, 0,
     'Mon: Rest · Tue: Easy 4k; comfortable throughout · '
     'Wed: Rest; gentle mobility · Thu: Easy 3k; stop feeling fresh · '
     'Fri: Rest; familiar carb-rich meals · Sat: Rest; prepare kit and fuel · '
     'Sun: RACE 42.195k; start 6:15–6:30/km with easy breathing; use Race Strategy; slow or walk if needed',
     'Race week'),
]

SOURCES = [
    ('Official Munich Marathon: 11 October 2026 and course services',
     'https://marathonmuenchen.org/en/the-marathon-one-lap-course-through-munich/'),
    ('Wang et al. (2023): endurance taper systematic review',
     'https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0282838'),
    ('Heaps et al. (1994): hydration and cardiovascular drift',
     'https://pubmed.ncbi.nlm.nih.gov/8157372/'),
    ('Australian Institute of Sport: carbohydrate during exercise',
     'https://www.ausport.gov.au/ais/nutrition/supplements/group_a/sports-foods2/sports-drink/how-and-when-do-i-use-it'),
]


def pace_clock(minutes):
    if pd.isna(minutes):
        return '—'
    seconds = int(float(minutes) * 60 + 0.5)
    return f'{seconds // 60}:{seconds % 60:02d}'


def review_metrics(runs, curves):
    """Freeze review evidence as of the review date; newer runs remain in live charts."""
    sample = runs[runs.Date.dt.date <= REVIEW_DATE].copy()
    weekly = sample.groupby('week_start').agg(
        km=('distance_km', 'sum'), count=('id', 'count'), longest=('distance_km', 'max'))
    weeks = pd.date_range('2026-07-06', '2026-09-14', freq='7D')
    weekly = weekly.reindex(weeks, fill_value=0)
    post = sample[sample.Date >= '2026-09-07']
    latest = sample[sample.id == 'i188527318']
    curve = curves.get('i188527318', {})
    stream = pd.DataFrame({k: curve.get(v, []) for k, v in
                           [('km', 'distance_km'), ('hr', 'hr'), ('pace', 'pace')]})
    segments = []
    for lo, hi in [(0, 5), (5, 10), (10, 15), (15, 20.02)]:
        s = stream[(stream.km >= lo) & (stream.km < hi)
                   & stream.pace.between(3, 10) & stream.hr.notna()]
        segments.append({'label': f'{lo}–{min(hi,20):g}', 'n': len(s),
                         'hr': s.hr.mean(), 'pace': s.pace.median()})
    return {'runs': sample, 'weekly': weekly, 'post': post, 'latest': latest,
            'curve': curve, 'segments': segments}


def _table(headers, rows):
    return ('<div class="table-responsive"><table class="table table-sm align-middle coaching-table">'
            '<thead><tr>' + ''.join(f'<th scope="col">{escape(h)}</th>' for h in headers)
            + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{escape(str(c))}</td>' for c in r) + '</tr>' for r in rows)
            + '</tbody></table></div>')


def analysis_html(metrics):
    runs, weekly = metrics['runs'], metrics['weekly']
    weekly_rows = [(d.strftime('%d %b'), f'{r.km:.1f}', int(r['count']), f'{r.longest:.1f}')
                   for d, r in weekly.iterrows()]
    comparison = runs[runs.id.isin(['i171669399', 'i173991235', 'i188527318'])]
    comp_rows = [(r.Date.strftime('%d %b'), f'{r.distance_km:.2f}', pace_clock(r.pace),
                  f'{r.avg_hr:.0f}') for r in comparison.itertuples()]
    all_rows = [(r.Date.strftime('%d %b %Y'), f'{r.distance_km:.2f}', pace_clock(r.pace),
                '—' if pd.isna(r.avg_hr) else f'{r.avg_hr:.0f}', r.Name)
               for r in runs.iloc[::-1].itertuples()]
    return f'''
    <section class="strategy-card mb-4">
      <h2 class="h5">Your training review · 22 September</h2>
      <p>All {len(runs)} recorded runs reviewed: {runs.distance_km.sum():.1f} km from
      18 March to 20 September. Your earlier base is meaningful, but the last two weeks
      are the best guide for what to do now.</p>
      <div class="row g-3">
        <div class="col-md-6"><h6>What supports your race</h6>
          <p>July and early August included 44.3, 51.4, 37.4, 55.1 and 61.0 km weeks,
          plus a 22.15 km run. You report feeling recovered, feeling fantastic on Sunday,
          and receiving your physio’s okay.</p>
          <h6>What limits the time target</h6>
          <p>There are no recorded runs from 10 August through 6 September.
          Seven runs since returning total 61.54 km. The latest long run grew from
          10.20 to 20.01 km (+96%) and supplied 61% of last week’s distance.</p>
          <p>The last four complete weeks average 15.4 km/week, including two zero-running
          weeks. The two return weeks average 30.8 km/week. Both matter: one describes
          the interruption, the other your current routine.</p>
        </div>
        <div class="col-md-6"><h6>Weekly running history</h6>
          {_table(['Week of', 'km', 'Runs', 'Longest km'], weekly_rows)}
        </div>
      </div>
      <h6>Comparable long runs</h6>
      {_table(['Date', 'km', 'Moving pace /km', 'Avg HR bpm'], comp_rows)}
      <p>Compared with 2 August, Sunday was about 18 seconds/km slower with HR 11 bpm higher.
      Conditions, route and sensor differences prevent treating this as a clean fitness test.
      The longer-run endurance needed for a sub-4 attempt has not been re-established in the log.</p>
      <p class="small mb-0">The export also contains 19 swims (18 pool, 1 open water),
      3 hikes and 2 padel sessions. They contribute general activity, but are not counted as running kilometres.
      CTL/ATL/Form describe recorded load, not injury recovery or marathon readiness.
      Missing activity records would change this assessment.</p>
    </section>
    <details class="strategy-card mb-4"><summary>All {len(runs)} runs reviewed</summary>
      {_table(['Date', 'km', 'Moving pace /km', 'Avg HR bpm', 'Session'], all_rows)}
    </details>'''


def remaining_plan_html():
    rows = [
        ('22 Sep · Tue', '5 km easy', 'Shorten if Sunday still feels present in your legs.'),
        ('23 Sep · Wed', 'Rest / gentle swim', 'Familiar physio exercises only.'),
        ('24 Sep · Thu', '6 km easy', 'Relaxed breathing; no fast finish.'),
        ('25–26 Sep', 'Rest / easy walking', 'Light familiar exercises Friday, no heavy strength.'),
        ('27 Sep · Sun', 'Up to 18 km or 110 min', 'Whichever comes first. Rehearse breakfast, shoes and fuel. Shorten to 12–14 km if not fully recovered.'),
        ('28 Sep · Mon', 'Rest', 'Check next-morning response.'),
        ('29 Sep · Tue', '5 km easy', 'Comfortable all the way.'),
        ('30 Sep · Wed', 'Rest', 'Light familiar physio exercises.'),
        ('1 Oct · Thu', '5 km easy', 'No fitness test.'),
        ('2–3 Oct', 'Rest / easy walking', 'Keep legs fresh.'),
        ('4 Oct · Sun', 'Up to 10 km easy', 'Finish with plenty left.'),
        ('5 Oct · Mon', 'Rest', 'Prioritize sleep and normal meals.'),
        ('6 Oct · Tue', '4 km easy', 'Easy means conversational.'),
        ('7 Oct · Wed', 'Rest', 'Gentle mobility.'),
        ('8 Oct · Thu', '3 km easy', 'Last short jog.'),
        ('9–10 Oct', 'Rest', 'Familiar carb-rich meals; prepare kit and fuel.'),
        ('11 Oct · Sun', 'Marathon · 42.195 km', 'Follow the Race Strategy tab; finish time is secondary to sustainable effort.'),
    ]
    return f'''<section class="strategy-card mb-4">
      <h2 class="h5">The remaining 19 days</h2>
      <p>Weekly training ceilings: <strong>29 km → 20 km → 7 km</strong> before the race.
      The race adds 42.195 km separately. Sunday’s 20 km was your last main long run.
      Another distance increase now would add fatigue with little time to absorb it.</p>
      <p>Keep the three-run rhythm you just completed. Run at 2–3/10 effort with full-sentence
      breathing, initially around 6:15–6:45/km or slower. Approximate easy HR reference:
      145–150 bpm; ease off if HR keeps rising, but do not force a number against how you feel.</p>
      {_table(['Date', 'Session', 'Purpose / adjustment'], rows)}
      <p class="mb-0">All distances are ceilings. Skip or shorten for fatigue; do not redistribute
      missed kilometres. Continue tolerated rehab, but avoid new heavy strength, hard hills,
      intervals and jumping sports. Recurring injury pain, altered stride or next-morning
      swelling/stiffness means stop running and follow up with your physio.</p>
    </section>'''


def strategy_html(metrics, curve_html):
    seg_rows = [(s['label'], '—' if not s['n'] else f"{s['hr']:.0f}",
                 pace_clock(s['pace'])) for s in metrics['segments']]
    sources = ''.join(f'<li><a href="{escape(url)}" target="_blank" rel="noopener">{escape(label)}</a></li>'
                      for label, url in SOURCES)
    stages = [
        ('0–5 km', '6:15–6:30/km or slower', 'Relaxed, full sentences; about 145–150 bpm once settled.', 'Let people go. Ignore brief start-line HR spikes; do not bank time.'),
        ('5–10 km', 'Stay relaxed; 6:10–6:25 only if easy', 'Prefer HR below about 155; effort 3/10.', 'If already 158–160, slow 15–30 sec/km and reassess after 3–5 min.'),
        ('10–25 km', 'Hold sustainable effort', 'Roughly 150–158 if stable; effort 3–4/10.', 'A sustained rise at unchanged pace is a reason to ease off, not a cue to chase a pace.'),
        ('25–32 km', 'Maintain; accept slower splits', 'Breathing controlled, form unchanged, fueling on track.', 'Do not accelerate at halfway. If HR/effort keeps climbing, slow or use run–walk.'),
        ('32–37 km', 'Optional small increase', 'Only if legs, breathing and HR trend remain controlled.', 'Try 5–10 sec/km faster for 1–2 km, reassess. Otherwise hold or slow.'),
        ('37–42.195 km', 'Finish by feel', 'No HR number grants permission to push through symptoms.', 'Increase gradually only if still comfortable. A controlled finish wins.'),
    ]
    return f'''<section class="strategy-card mb-4" style="border-color:#60a5fa">
      <div class="small text-info mb-2">RACE STRATEGY · REVIEWED 22 SEPTEMBER</div>
      <h2>Start patiently. Decide about speed after 32 km.</h2>
      <p>My recommendation is a finish-focused marathon with even effort and the option of a small
      late acceleration. Start around <strong>6:15–6:30/km</strong> and let breathing and HR set
      the limit. The original sub-4 pace (~5:41/km) is too aggressive as the opening plan given
      the interruption and Sunday’s HR rise.</p>
      <p class="mb-0">For context, 6:10–6:30/km across the full distance equals about
      <strong>4:20–4:34</strong> before extra stops. This is pace arithmetic, not a finish prediction
      or a target you must protect. A slower finish or planned walk breaks may be appropriate.</p>
    </section>
    <div class="row g-3 mb-4">
      <div class="col-lg-7"><section class="strategy-card h-100">
        <h6>What Sunday’s pulse tells us</h6>
        <p>20.01 km · 1:55:34 moving · 5:46/km · 158 bpm average.</p>
        {curve_html}
        {_table(['Segment km', 'Sampled mean HR', 'Median sampled pace /km'], seg_rows)}
        <p class="small mb-0">These are approximate summaries of sparse curve samples, not official
        splits or a time-weighted drift test. Samples outside 3–10 min/km are excluded from this
        table (1 of 165); charts show the original samples. The final 5 km averaged about
        166 bpm without faster sampled pace. The export lacks elapsed time, elevation, weather,
        fluid intake and confirmed sensor type, so the cause cannot be isolated.</p>
      </section></div>
      <div class="col-lg-5"><section class="strategy-card h-100">
        <h6>Use HR as a brake, alongside effort</h6>
        <p>Your reported maximum is <strong>around 190 bpm</strong>. If accurate, 158 is about 83%
        and 166 about 87% of that value. Neither percentage establishes your aerobic or lactate
        threshold. We do not have tested zones.</p>
        <p>The numbers below are deliberately cautious starting references based on your runs,
        not validated race zones, medical limits or a formula from age. Do not speed up to reach them.</p>
        <p>Use a 3–5 minute trend plus breathing. Check a sudden implausible reading against effort
        and sensor contact; a chest strap can help if available and already familiar.</p>
        <p>Heat, hydration, accumulated fatigue and sensor error can change HR. They are possibilities,
        not a diagnosis of Sunday’s run. On a warm day, keep effort steady and accept slower pace.</p>
        <p class="mb-0">Aim for a steady effort, not a forced negative split. Running the second half
        faster is an option earned late in the race, never an obligation.</p>
      </section></div>
    </div>
    <section class="strategy-card mb-4"><h6>Race stages</h6>
      {_table(['Stage', 'Pace approach', 'HR / effort check', 'Action'], stages)}
    </section>
    <div class="row g-3 mb-4">
      <div class="col-md-6"><section class="strategy-card h-100">
        <h6>If HR climbs or you need to slow</h6>
        <p>Before 25 km, sustained HR above about 160 at an unchanged or slower pace is a
        pacing alert. Slow 15–30 sec/km, check breathing, take your scheduled fuel and sip to thirst.
        Reassess after 3–5 minutes. Do not try to lower HR by forcing water.</p>
        <p>If effort stays high, walk 30–60 seconds, then restart slower. Repeat as needed;
        9 minutes easy running / 1 minute walking is an option to rehearse on 27 September.</p>
        <p class="mb-0">If you lose time in crowds or at a station, return to your sustainable effort.
        Never surge to repay it. A brief hill-related HR rise differs from a persistent rise on flat ground.</p>
      </section></div>
      <div class="col-md-6"><section class="strategy-card h-100">
        <h6>If you feel fantastic early or late</h6>
        <p>Before 30–32 km: keep holding back, even if it feels very easy. Sunday’s final
        kilometres already showed extra cardiovascular strain while you felt good.</p>
        <p>After 32 km: only accelerate if there is no injury pain, stride is normal, breathing
        controlled, fuel tolerated, and HR is not already rising sharply. Increase just 5–10 sec/km
        and reassess after 1–2 km.</p>
        <p class="mb-0">Increasing injury pain or altered gait means stop. Chest pain, faintness,
        confusion or unusual severe breathlessness means stop and seek race medical help.
        These symptoms override every pace or HR instruction.</p>
      </section></div>
    </div>
    <section class="strategy-card mb-4"><h6>Fuel from the start</h6>
      <p>You reported one gel at 10 km and a bagel with avocado beforehand. If the gel had
      20–30 g carbohydrate, that supplied only about <strong>10–16 g/hour</strong> during the run,
      excluding any unreported drink carbs. The gel size and fluid intake are unknown.
      This was modest fueling, but it does not prove why HR rose. Formal carb loading was
      not required just to complete this training run.</p>
      <p>Use 27 September to practice <strong>30–60 g carbohydrate/hour</strong> with familiar products,
      aiming toward 45–60 only if comfortable. An example is a 25 g gel at 20, 50 and 80 minutes,
      then every 30 minutes: approximately 50 g/hour over a longer run. Count sports drink carbs too.
      Do not jump to 90 g/hour on race day without prior practice.</p>
      <p class="mb-0">Drink to thirst in small regular amounts; do not force a fixed volume or chase
      HR with water. Take water with gels as their label recommends. Carry familiar gels: the organiser
      currently lists on-course gels only from km 26.5, much too late for your first fuel.</p>
    </section>
    <section class="strategy-card"><h6>Evidence and limits</h6>
      <p class="small">This is a dated coaching judgment using all supplied activities through 20 September,
      the HR/pace curves, load history through 22 September and your recovery report. Your physio okay
      is accepted as reported; the pace and distance recommendations are our training choices.
      The fixed review does not silently change when new data syncs. Taper research supports reducing
      volume before competition; it does not validate a specific post-injury marathon plan.</p>
      <ul class="small">{sources}</ul>
    </section>'''


def nutrition_html():
    return '''<div class="row g-3">
      <div class="col-md-6"><section class="strategy-card h-100">
        <h6>27 September: rehearse your race routine</h6>
        <p>Eat a familiar carbohydrate-rich breakfast 2–3 hours beforehand. A bagel can work;
        use less avocado/fat if it feels heavy and add a familiar easy carb such as jam or banana.
        Do not add a long run to test food.</p>
        <p class="mb-0">Practice the same gels, timing, shoes and carrying method you intend to use.
        Aim for 30–60 g carbohydrate/hour; use the amount you tolerate rather than forcing the
        top end. Example: 25 g gels at 20, 50 and 80 minutes, with water according to the label.</p>
      </section></div>
      <div class="col-md-6"><section class="strategy-card h-100">
        <h6>Race week and race morning</h6>
        <p>Keep meals regular as running volume drops. For the last 36–48 hours, increase familiar
        carbohydrate foods and keep fat/fibre moderate if they upset your stomach. Spread food
        across meals and snacks instead of one huge dinner.</p>
        <p class="mb-0">Repeat your practiced breakfast 2–3 hours before your start, and start normally
        hydrated. Avoid new supplements, unfamiliar caffeinated gels or a large last-minute drink.</p>
      </section></div>
      <div class="col-md-6"><section class="strategy-card h-100">
        <h6>During the marathon</h6>
        <p>Start fueling at about 20 minutes and continue regularly. Use the carbohydrate rate
        rehearsed successfully on 27 September, with 45–60 g/hour a useful aim if tolerated.</p>
        <p class="mb-0">If 25 g gels every 30 minutes work for you, plan 9 gels through 4:20 plus
        one spare for a longer race; reduce gel intake to account for any carb drink. Carry your
        own familiar supply. Drink to thirst and follow each gel’s water instructions.</p>
      </section></div>
      <div class="col-md-6"><section class="strategy-card h-100">
        <h6>Recovery and adjustment</h6>
        <p>After runs, eat a normal meal or snack containing carbs and protein, and rehydrate
        steadily to thirst. Continue familiar light rehab and prioritize sleep.</p>
        <p class="mb-0">If gels cause nausea, ease the pace and take small, tolerable amounts;
        do not force more fuel or water. Persistent or severe symptoms mean seek assistance.
        HR alone cannot diagnose dehydration or low carbohydrate availability.</p>
      </section></div>
    </div><p class="small mt-3">Sources and the reasoning behind these choices are linked in Race Strategy.</p>'''
