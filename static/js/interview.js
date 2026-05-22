/**
 * Mock Interview — session UI + backend API.
 * Timer and questions begin only after "Start Interview".
 */

(function () {
  const SESSION_EL = document.getElementById('iv-session');
  if (!SESSION_EL) return;

  const TOTAL_Q = parseInt(SESSION_EL.dataset.total || '8', 10);
  const TIMER_TOTAL = parseInt(SESSION_EL.dataset.timerTotal || '900', 10);
  const RING_CIRC = 364;
  const TIMER_RING_CIRC = 113;

  const state = {
    sessionId: null,
    started: false,
    currentQ: 0,
    totalQ: TOTAL_Q,
    currentQuestion: '',
    hintsLeft: 2,
    timerSec: TIMER_TOTAL,
    timerTotal: TIMER_TOTAL,
    timerInterval: null,
    history: [],
    redoStack: [],
    answered: false,
  };

  const $ = (id) => document.getElementById(id);

  function formatTime(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function setThinking(label, showDots) {
    const lbl = $('iv-thinking-label');
    const dots = $('iv-thinking-dots');
    if (lbl) lbl.textContent = label;
    if (dots) dots.style.display = showDots ? 'flex' : 'none';
  }

  function updateQuestionCounter() {
    const cur = $('iv-q-current');
    const tot = $('iv-q-total');
    if (cur) cur.textContent = String(Math.max(0, state.currentQ) || '—');
    if (tot) tot.textContent = String(state.totalQ);
  }

  function updateTimerUI() {
    const display = $('iv-timer-display');
    const ring = $('iv-timer-ring');
    if (display) display.textContent = formatTime(state.timerSec);
    if (ring) {
      const pct = state.timerTotal > 0 ? state.timerSec / state.timerTotal : 0;
      ring.setAttribute('stroke-dashoffset', String(TIMER_RING_CIRC * (1 - pct)));
    }
  }

  function stopTimer() {
    if (state.timerInterval) {
      clearInterval(state.timerInterval);
      state.timerInterval = null;
    }
  }

  function startTimer() {
    stopTimer();
    updateTimerUI();
    state.timerInterval = setInterval(() => {
      if (!state.started || state.timerSec <= 0) {
        if (state.timerSec <= 0) onTimeUp();
        return;
      }
      state.timerSec -= 1;
      updateTimerUI();
    }, 1000);
  }

  async function onTimeUp() {
    stopTimer();
    setThinking('Time is up', false);
    if (state.sessionId) {
      await api('POST', `/interview/api/session/${state.sessionId}/end`, { completed: true });
    }
    alert('Time is up! Your interview session has ended.');
    showLobby();
  }

  function setLobbyVisible(show) {
    const lobby = $('iv-lobby');
    if (lobby) lobby.style.display = show ? 'flex' : 'none';
    SESSION_EL.classList.toggle('iv-session--lobby', show);
    SESSION_EL.classList.toggle('iv-session--live', !show);
    setRoomDisabled(show);
  }

  function setRoomDisabled(disabled) {
    ['iv-answer', 'iv-submit-btn', 'iv-hint-btn', 'iv-clear-btn', 'iv-next-btn'].forEach((id) => {
      const el = $(id);
      if (el) el.disabled = disabled || (id === 'iv-submit-btn' && (!state.currentQuestion || !state.started));
    });
  }

  function showLobby() {
    state.started = false;
    stopTimer();
    state.timerSec = state.timerTotal;
    updateTimerUI();
    setLobbyVisible(true);
    setThinking('Alexia is ready', false);
    $('iv-resume-btn')?.style.setProperty('display', window.__IV_RESUME__ ? 'inline-flex' : 'none');
  }

  function enterLiveRoom() {
    setLobbyVisible(false);
    state.started = true;
    startTimer();
    setRoomDisabled(false);
    updateCharCount();
  }

  function applySessionPayload(s) {
    if (!s) return;
    state.sessionId = s.id;
    state.currentQ = s.current_index || 0;
    state.totalQ = s.total_questions || TOTAL_Q;
    state.hintsLeft = s.hints_remaining ?? 2;
    state.timerTotal = s.timer_total_sec || TIMER_TOTAL;
    state.timerSec = s.timer_remaining_sec ?? state.timerTotal;
    state.currentQuestion = s.question || '';

    const hintsEl = $('iv-hints-left');
    if (hintsEl) hintsEl.textContent = String(state.hintsLeft);
    $('iv-hint-btn').disabled = state.hintsLeft <= 0;

    updateQuestionCounter();
    updateTimerUI();

    const bubble = $('iv-question-text');
    if (bubble && state.currentQuestion) bubble.textContent = state.currentQuestion;

    const meta = s.question_meta || {};
    const tip = $('iv-tip-text');
    const tips = meta.what_interviewers_look_for || [];
    if (tip && tips.length) tip.textContent = `Tip: ${tips[0]}`;

    if (s.started) {
      setThinking('Alexia is listening', false);
    }
  }

  async function api(method, url, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Request failed');
    return data;
  }

  function resetScores() {
    ['clarity', 'technical', 'accuracy', 'structure', 'communication'].forEach((key) => {
      const scoreEl = $(`score-${key}`);
      const barEl = $(`bar-${key}`);
      if (scoreEl) {
        scoreEl.textContent = '— / 10';
        scoreEl.classList.remove('has-score');
      }
      if (barEl) barEl.style.width = '0%';
    });
    const overall = $('iv-overall-score');
    const ring = $('iv-score-ring');
    const note = $('iv-score-note');
    if (overall) overall.textContent = '—';
    if (ring) ring.setAttribute('stroke-dashoffset', String(RING_CIRC));
    if (note) note.textContent = 'Answer to get score';
    $('iv-feedback')?.classList.remove('show');
    $('iv-next-row')?.classList.remove('show');
    state.answered = false;
  }

  function setMetric(key, value) {
    const v = Math.max(0, Math.min(10, Number(value) || 0));
    const scoreEl = $(`score-${key}`);
    const barEl = $(`bar-${key}`);
    if (scoreEl) {
      scoreEl.textContent = `${v.toFixed(1)} / 10`;
      scoreEl.classList.add('has-score');
    }
    if (barEl) barEl.style.width = `${v * 10}%`;
  }

  function applyFeedback(fb) {
    const metrics = fb.metric_scores || {};
    setMetric('clarity', metrics.clarity);
    setMetric('technical', metrics.technical_depth);
    setMetric('accuracy', metrics.accuracy);
    setMetric('structure', metrics.structure);
    setMetric('communication', metrics.communication);

    const score = Math.max(0, Math.min(100, Number(fb.score || 0)));
    const overall = $('iv-overall-score');
    const ring = $('iv-score-ring');
    const note = $('iv-score-note');
    if (overall) overall.textContent = String(Math.round(score));
    if (ring) ring.setAttribute('stroke-dashoffset', String(RING_CIRC - (score / 100) * RING_CIRC));
    if (note) note.textContent = `${fb.grade || 'B'} grade · ${fb.confidence_signal || 'Medium'} confidence`;

    const gradeEl = $('iv-feedback-grade');
    const textEl = $('iv-feedback-text');
    if (gradeEl) gradeEl.textContent = `${fb.grade || 'B'} · ${score}/100`;
    if (textEl) textEl.textContent = fb.overall_feedback || '';
    $('iv-feedback')?.classList.add('show');
    $('iv-next-row')?.classList.add('show');
    state.answered = true;

    const followUp = fb.interviewer_follow_up;
    if (followUp) {
      const tip = $('iv-tip-text');
      if (tip) tip.textContent = `Follow-up Alexia may ask: ${followUp}`;
    }
  }

  async function startInterview() {
    const loading = $('iv-lobby-loading');
    const startBtn = $('iv-start-btn');
    if (loading) loading.style.display = 'block';
    if (startBtn) startBtn.disabled = true;

    try {
      let sessionId = state.sessionId;
      if (!sessionId) {
        const prep = await api('POST', '/interview/api/session/prepare', {
          career_title: SESSION_EL.dataset.career,
          round_label: SESSION_EL.dataset.round,
        });
        sessionId = prep.session.id;
        state.sessionId = sessionId;
      }

      const data = await api('POST', `/interview/api/session/${sessionId}/start`);
      applySessionPayload(data.session);

      const ta = $('iv-answer');
      if (ta) {
        ta.value = '';
        pushHistory('');
      }
      resetScores();
      enterLiveRoom();
      window.__IV_RESUME__ = null;
    } catch (err) {
      alert('Could not start interview: ' + err.message);
      showLobby();
    } finally {
      if (loading) loading.style.display = 'none';
      if (startBtn) startBtn.disabled = false;
    }
  }

  async function resumeInterview() {
    const s = window.__IV_RESUME__;
    if (!s || !s.id) return startInterview();

    state.sessionId = s.id;
    applySessionPayload(s);
    resetScores();
    enterLiveRoom();
    window.__IV_RESUME__ = null;
    $('iv-resume-btn')?.style.setProperty('display', 'none');
  }

  async function submitAnswer() {
    const answer = $('iv-answer')?.value.trim() || '';
    if (!answer || answer.length < 10 || !state.currentQuestion || !state.sessionId) return;

    const btn = $('iv-submit-btn');
    const loading = $('iv-loading');
    if (btn) btn.disabled = true;
    loading?.classList.add('show');
    setThinking('Evaluating your answer…', true);

    try {
      const data = await api('POST', `/interview/api/session/${state.sessionId}/submit`, { answer });
      applyFeedback(data.feedback || {});
      if (data.session) applySessionPayload(data.session);
      if (data.aptitude?.evaluation?.summary) {
        const tip = $('iv-tip-text');
        if (tip) tip.textContent = data.aptitude.evaluation.summary;
      }
      setThinking('Alexia is listening', false);
    } catch (err) {
      setThinking('Alexia is listening', false);
      alert('Evaluation error: ' + err.message);
    } finally {
      loading?.classList.remove('show');
      updateCharCount();
    }
  }

  async function nextQuestion() {
    if (!state.sessionId) return;
    if (state.currentQ >= state.totalQ) {
      await api('POST', `/interview/api/session/${state.sessionId}/end`, { completed: true });
      alert('Interview complete! Great work.');
      showLobby();
      return;
    }

    setThinking('Alexia is thinking', true);
    resetScores();
    const ta = $('iv-answer');
    if (ta) {
      ta.value = '';
      pushHistory('');
    }
    updateCharCount();

    try {
      const data = await api('POST', `/interview/api/session/${state.sessionId}/next`);
      if (data.completed) {
        alert('Interview complete!');
        showLobby();
        return;
      }
      applySessionPayload(data.session);
      setThinking('Alexia is listening', false);
    } catch (err) {
      setThinking('Alexia is ready', false);
      alert(err.message);
    }
  }

  function pushHistory(text) {
    const ta = $('iv-answer');
    if (!ta) return;
    state.history.push(ta.value);
    if (state.history.length > 50) state.history.shift();
    state.redoStack = [];
    updateUndoRedo();
  }

  function updateUndoRedo() {
    $('iv-undo-btn').disabled = state.history.length < 2;
    $('iv-redo-btn').disabled = state.redoStack.length === 0;
  }

  function updateCharCount() {
    const ta = $('iv-answer');
    const count = $('iv-char-count');
    const btn = $('iv-submit-btn');
    const len = ta ? ta.value.length : 0;
    if (count) count.textContent = String(len);
    if (btn) {
      btn.disabled = !state.started || !state.currentQuestion || len < 10 || $('iv-loading')?.classList.contains('show');
    }
  }

  function bindTabs() {
    document.querySelectorAll('.iv-answer-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        if (tab.classList.contains('soon')) return;
        const name = tab.dataset.tab;
        document.querySelectorAll('.iv-answer-tab').forEach((t) => {
          t.classList.toggle('active', t === tab);
          t.setAttribute('aria-selected', t === tab ? 'true' : 'false');
        });
        document.querySelectorAll('.iv-answer-pane').forEach((p) => {
          p.classList.toggle('active', p.id === `pane-${name}`);
        });
      });
    });
  }

  function bindHints() {
    $('iv-hint-btn')?.addEventListener('click', async () => {
      if (!state.sessionId || state.hintsLeft <= 0) return;
      try {
        const data = await api('POST', `/interview/api/session/${state.sessionId}/hint`);
        state.hintsLeft = data.hints_remaining;
        $('iv-hints-left').textContent = String(state.hintsLeft);
        $('iv-tip-text').textContent = data.hint || '';
        if (state.hintsLeft <= 0) $('iv-hint-btn').disabled = true;
      } catch (err) {
        alert(err.message);
      }
    });
  }

  function bindAnswerTools() {
    const ta = $('iv-answer');
    if (!ta) return;

    let debounce;
    ta.addEventListener('input', () => {
      updateCharCount();
      clearTimeout(debounce);
      debounce = setTimeout(() => pushHistory(ta.value), 400);
    });

    $('iv-clear-btn')?.addEventListener('click', () => {
      pushHistory(ta.value);
      ta.value = '';
      updateCharCount();
    });

    $('iv-undo-btn')?.addEventListener('click', () => {
      if (state.history.length < 2) return;
      state.redoStack.push(state.history.pop());
      ta.value = state.history[state.history.length - 1] || '';
      updateCharCount();
      updateUndoRedo();
    });

    $('iv-redo-btn')?.addEventListener('click', () => {
      if (!state.redoStack.length) return;
      const val = state.redoStack.pop();
      state.history.push(val);
      ta.value = val;
      updateCharCount();
      updateUndoRedo();
    });

    $('iv-submit-btn')?.addEventListener('click', submitAnswer);
    $('iv-next-btn')?.addEventListener('click', nextQuestion);

    $('iv-report-btn')?.addEventListener('click', () => {
      alert('Thanks — issue reporting will be wired in the next release.');
    });

    $('iv-end-btn')?.addEventListener('click', async (e) => {
      if (!confirm('End this interview session?')) {
        e.preventDefault();
        return;
      }
      if (state.sessionId) {
        await api('POST', `/interview/api/session/${state.sessionId}/end`, { completed: false });
      }
      stopTimer();
    });
  }

  function init() {
    state.timerTotal = TIMER_TOTAL;
    state.timerSec = TIMER_TOTAL;
    updateTimerUI();
    updateQuestionCounter();
    showLobby();

    if (window.__IV_RESUME__) {
      $('iv-resume-btn')?.style.setProperty('display', 'inline-flex');
      $('iv-lobby-title').textContent = 'Continue your interview?';
    }

    $('iv-start-btn')?.addEventListener('click', startInterview);
    $('iv-resume-btn')?.addEventListener('click', resumeInterview);

    bindTabs();
    bindHints();
    bindAnswerTools();
    pushHistory('');
    if (window.lucide) lucide.createIcons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
