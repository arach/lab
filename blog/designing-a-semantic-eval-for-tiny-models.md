# Designing A Semantic Eval For Tiny Models

> If the model is tiny, the benchmark should ask whether it helps.

<!-- METADATA
slug: designing-a-semantic-eval-for-tiny-models
date: 2026-04-06
tags: evals, on-device-ml, tiny-models, semantic-evaluation, local-intelligence
author: Arach
description: A reader-first walkthrough of a new semantic eval for tiny local models, including what it measures, how the scores work, and what the first local runs show.
-->

<section id="page-1" class="article-page-section">
  <div class="article-page-kicker">Page 1</div>
  <h2>What this eval is for</h2>

  <p>
    Small local models are not miniature API assistants. They are better thought
    of as compact semantic helpers.
  </p>

  <p>
    Give them a short memo and a narrow question, and they can often do useful
    work: suggest a title, identify the user's intent, rewrite a messy note,
    pull out the next step, or ask the one clarifying question that would make
    the memo usable.
  </p>

  <p>
    That is the job this benchmark is designed to measure.
  </p>

  <h3>The core question</h3>

  <p>
    The point of this eval is not to ask whether a tiny model can emit a
    perfect JSON packet.
  </p>

  <p>
    The point is to ask whether it can do small semantic jobs that make a
    voice-memo app feel smarter.
  </p>

  <ul>
    <li>Can it name the note?</li>
    <li>Can it identify the user's intent?</li>
    <li>Can it extract the next step?</li>
    <li>Can it clean up a messy transcript?</li>
    <li>Can it notice reminder or calendar intent?</li>
    <li>Can it retrieve a related note?</li>
    <li>Can it ask a useful follow-up question?</li>
  </ul>

  <h3>The design rule</h3>

  <blockquote>
    <p>Prefer plain-language answers unless structure is truly the product requirement.</p>
  </blockquote>

  <p>
    That means this pack does <strong>not</strong> default to exact JSON, nested
    field contracts, tool-call packets, or agent-loop outputs.
  </p>

  <p>
    Those things may matter elsewhere in the stack. They are just not the right
    default test for a tiny local model.
  </p>

  <h3>The card set</h3>

  <p>The first version of the pack uses nine app moments:</p>

  <ol>
    <li>Give this memo a useful title</li>
    <li>What kind of memo is this?</li>
    <li>What should the user do next?</li>
    <li>Rewrite this memo more clearly</li>
    <li>What matters most?</li>
    <li>Should this become a reminder?</li>
    <li>Should this become a calendar event?</li>
    <li>What follow-up question should we ask?</li>
    <li>Which old memo is most similar?</li>
  </ol>

  <p>
    Each card is short, concrete, and close to a real product moment. That
    makes the pack easier to audit and much harder to fool ourselves with.
  </p>
</section>

<section id="page-2" class="article-page-section">
  <div class="article-page-kicker">Page 2</div>
  <h2>How the scores work</h2>

  <p>
    Every card is graded on three dimensions. They are meant to answer three
    different questions, not one blended one.
  </p>

  <table>
    <thead>
      <tr>
        <th>Dimension</th>
        <th>What it asks</th>
        <th>What a high score means</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>task</code></td>
        <td>Did the model get the substance right?</td>
        <td>The answer is actually useful and semantically correct.</td>
      </tr>
      <tr>
        <td><code>clarity</code></td>
        <td>Was the answer concise and readable?</td>
        <td>The answer is clean enough for a user or wrapper layer to use.</td>
      </tr>
      <tr>
        <td><code>discipline</code></td>
        <td>Did it avoid filler, evasiveness, or prompt-breakage habits?</td>
        <td>The model stays well-behaved while answering.</td>
      </tr>
    </tbody>
  </table>

  <h3>How a card score is calculated</h3>

  <p>The overall card score is weighted like this:</p>

  <ul>
    <li><code>75%</code> task</li>
    <li><code>25%</code> supporting quality</li>
  </ul>

  <p>The supporting quality is the average of <code>clarity</code> and <code>discipline</code>.</p>

  <p>So if a card gets:</p>

  <ul>
    <li><code>task = 1.0</code></li>
    <li><code>clarity = 0.5</code></li>
    <li><code>discipline = 1.0</code></li>
  </ul>

  <p>
    then the supporting quality is <code>0.75</code>, and the overall card
    score is <code>0.9375</code>.
  </p>

  <p>
    That weighting is intentional. A semantically right answer should still do
    well even if it is a little rough.
  </p>

  <h3>What counts as a pass</h3>

  <p>A card passes when:</p>

  <ul>
    <li>the <code>task</code> dimension passes in full</li>
    <li>the supporting dimensions are at least decent overall</li>
  </ul>

  <p>In practice, that means:</p>

  <ul>
    <li>a semantically wrong answer should fail</li>
    <li>a semantically right but slightly messy answer can still pass</li>
    <li>a polished but semantically wrong answer should not</li>
  </ul>

  <h3>How to interpret score shapes</h3>

  <table>
    <thead>
      <tr>
        <th>Score pattern</th>
        <th>What it usually means</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>High task, high clarity, high discipline</td>
        <td>The model is genuinely strong for this pack.</td>
      </tr>
      <tr>
        <td>High task, lower clarity</td>
        <td>The model understands the memo but answers a little messily.</td>
      </tr>
      <tr>
        <td>Low task, high clarity</td>
        <td>The answer sounds neat but gets the job wrong.</td>
      </tr>
      <tr>
        <td>High discipline, low task</td>
        <td>The model is well-behaved but not very useful.</td>
      </tr>
    </tbody>
  </table>

  <p>
    For this benchmark, <code>task_score</code> is the main signal to trust.
    The other two dimensions help explain <em>why</em> a model looks good or
    bad.
  </p>
</section>

<section id="page-3" class="article-page-section">
  <div class="article-page-kicker">Page 3</div>
  <h2>What the first local runs show</h2>

  <p>
    Once the pack was in place, we ran it locally through MLX on a few small
    on-device models.
  </p>

  <table>
    <thead>
      <tr>
        <th>Model</th>
        <th>Pass</th>
        <th>Task</th>
        <th>Clarity</th>
        <th>Discipline</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>Qwen2.5 0.5B Instruct 4bit</code></td>
        <td><code>6/9</code></td>
        <td><code>0.759</code></td>
        <td><code>0.926</code></td>
        <td><code>1.000</code></td>
      </tr>
      <tr>
        <td><code>Llama 3.2 1B Instruct 4bit</code></td>
        <td><code>5/9</code></td>
        <td><code>0.648</code></td>
        <td><code>0.852</code></td>
        <td><code>0.889</code></td>
      </tr>
      <tr>
        <td><code>Qwen2.5 1.5B Instruct 4bit</code></td>
        <td><code>4/9</code></td>
        <td><code>0.611</code></td>
        <td><code>0.870</code></td>
        <td><code>1.000</code></td>
      </tr>
    </tbody>
  </table>

  <p>
    The important thing is not that these numbers are perfect. They are not.
  </p>

  <p>
    The important thing is that the benchmark is now both winnable and
    interpretable.
  </p>

  <p>
    The misses are things like:
  </p>

  <ul>
    <li>saying <code>Yes</code> to the calendar question without describing the event</li>
    <li>answering the memo question instead of asking a follow-up question</li>
    <li>choosing the wrong memo type</li>
  </ul>

  <p>
    Those are real semantic misses. They tell us something useful about the
    models.
  </p>

  <h3>What this benchmark tells us now</h3>

  <ul>
    <li>It is possible for a tiny model to look clearly useful on this pack.</li>
    <li>The pack still produces spread across local models.</li>
    <li>The differences are easy to interpret by eye.</li>
  </ul>

  <p>
    That is what I wanted from this reset: a benchmark that is fair to small
    models without becoming so soft that every model looks the same.
  </p>

  <h3>What happens next</h3>

  <p>The next steps are straightforward:</p>

  <ul>
    <li>tighten the cards that are still a little loose</li>
    <li>add a few harder semantic app moments</li>
    <li>keep structured-output tests as a separate layer instead of the default one</li>
  </ul>

  <p>
    Tiny models still need evaluation. They just need to be evaluated on the
    job they are actually being asked to do.
  </p>
</section>
