
// ----- Interactions -----
function toggleHint(btn) {
  const hint = btn.nextElementSibling;
  if(hint.style.display === 'none' || hint.style.display === '') {
    hint.style.display = 'block';
    btn.textContent = 'Hide Hint';
    btn.style.color = '#fff';
    btn.style.borderColor = '#fff';
  } else {
    hint.style.display = 'none';
    btn.textContent = '💡 Show Hint';
    btn.style.color = 'var(--text-muted)';
    btn.style.borderColor = 'rgba(255,255,255,0.2)';
  }
}

function runSimulation(btn) {
  const orig = btn.innerHTML;
  btn.innerHTML = '⏳ Compiling & Running...';
  btn.style.opacity = '0.8';
  btn.disabled = true;
  setTimeout(() => {
    btn.innerHTML = '✅ All 14 Test Cases Passed!';
    btn.style.background = 'var(--success)';
    btn.style.opacity = '1';
    btn.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.4)';
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.style.background = 'var(--primary)';
      btn.style.boxShadow = '0 4px 15px rgba(124,58,237,0.3)';
      btn.disabled = false;
    }, 4000);
  }, 1500);
}

function showToast(title, msg, isError=false) {
  const toast = document.getElementById('toast');
  document.getElementById('toast-title').textContent = title;
  document.getElementById('toast-msg').textContent = msg;
  toast.style.borderLeftColor = isError ? 'var(--error)' : 'var(--success)';
  document.getElementById('toast-icon').textContent = isError ? '❌' : '✅';
  
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 4000);
}

// ----- Timer -----
let timerInterval = null;
let seconds = 1800; // 30 min
function startTimer() {
  if (timerInterval) return;
  document.getElementById('btnStart').textContent = '⏸ Pause Interview';
  document.getElementById('btnStart').onclick = pauseTimer;
  document.getElementById('btnStart').style.background = 'var(--secondary)';
  
  timerInterval = setInterval(() => {
    if (seconds <= 0) { 
        clearInterval(timerInterval); 
        showToast('Time is up!', 'Interview session automatically concluded.'); 
        timerInterval = null;
        return; 
    }
    seconds--;
    const m = String(Math.floor(seconds/60)).padStart(2,'0');
    const s = String(seconds%60).padStart(2,'0');
    document.getElementById('timer').textContent = m+':'+s;
  }, 1000);
}
function pauseTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
  document.getElementById('btnStart').textContent = '▶ Resume Interview';
  document.getElementById('btnStart').style.background = 'var(--primary)';
  document.getElementById('btnStart').onclick = startTimer;
}
function resetTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
  seconds = 1800;
  document.getElementById('timer').textContent = '30:00';
  document.getElementById('btnStart').textContent = '▶ Start Interview';
  document.getElementById('btnStart').style.background = 'var(--primary)';
  document.getElementById('btnStart').onclick = startTimer;
}

// ----- API Submission -----
async function submitFeedback() {
  const company = document.getElementById('fb_company').value;
  const role = document.getElementById('fb_role').value;
  const rawQ = document.getElementById('fb_questions').value.trim();
  const confidence = parseInt(document.getElementById('fb_confidence').value);
  const difficulty = parseInt(document.getElementById('fb_difficulty').value);
  const btn = document.getElementById('btnSubmit');

  if (!rawQ) {
    showToast('Missing Insight', 'Please add the questions you struggled with to update your metrics.', true);
    document.getElementById('fb_questions').focus();
    return;
  }

  const questions_faced = rawQ.split('\n').map(q => q.trim()).filter(q => q.length > 2);
  const payload = { company, role, questions_faced, confidence_level: confidence, difficulty_level: difficulty };

  btn.innerHTML = '⏳ Synchronizing with OrchestrAI Analytics...';
  btn.disabled = true;

  try {
    const resp = await fetch(window.location.origin + '/log-feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (resp.ok && data.status === 'ok') {
      showToast('Interview Logged Successfully!', 'Your readiness score and career strategy have been updated.');
      document.getElementById('fb_questions').value = '';
    } else {
      showToast('Sync Error', data.message || 'Failed to save feedback analytics.', true);
    }
  } catch(e) {
    showToast('Connection Error', 'Could not reach OrchestrAI agent network: ' + e.message, true);
  } finally {
    setTimeout(() => {
      btn.innerHTML = '📤 Log Interview & Update Analytics';
      btn.disabled = false;
    }, 1000);
  }
}

// ----- AI Interview Chat -----
var chatHistory = [];
var chatCompany = "RefinedScience";
var chatRole = "Data Engineering Intern";
var currentDifficulty = "medium";
var sessionEvaluations = [];
var sessionCodingScore = null;
var portfolioProjects = [];
// Load portfolio from page meta if available
try {
  var pmeta = document.getElementById('portfolioMeta');
  if (pmeta) portfolioProjects = JSON.parse(pmeta.dataset.projects || '[]');
} catch(e) {}

function addChatBubble(role, text, qtype) {
  var messages = document.getElementById('chatMessages');
  var empty = document.getElementById('chatEmpty');
  if (empty) empty.style.display = 'none';

  var bubble = document.createElement('div');
  bubble.className = 'chat-bubble ' + role;

  var label = document.createElement('span');
  label.className = 'bubble-label';
  label.textContent = role === 'ai' ? '🤖 AI Interviewer' : '👤 You';
  bubble.appendChild(label);

  var contentWrapper = document.createElement('div');
  var contentHTML = '';
  if (qtype) {
    var color = qtype === 'technical' ? '#3b82f6' : (qtype === 'coding' ? '#10b981' : '#8b5cf6');
    contentHTML += `<span class="qtype-badge" style="background:${color}">${qtype.toUpperCase()}</span>`;
  }
  contentHTML += text;
  contentWrapper.innerHTML = contentHTML;
  bubble.appendChild(contentWrapper);

  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

function showTypingIndicator() {
  var messages = document.getElementById('chatMessages');
  var indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.id = 'typingIndicator';
  indicator.innerHTML = '<span></span><span></span><span></span>';
  messages.appendChild(indicator);
  messages.scrollTop = messages.scrollHeight;
}

function removeTypingIndicator() {
  var el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

async function callInterviewAPI(userAnswer) {
  var payload = {
    company: chatCompany,
    role: chatRole,
    question_history: chatHistory,
    user_answer: userAnswer || null,
    difficulty: currentDifficulty,
    portfolio_projects: portfolioProjects
  };
  var resp = await fetch(window.location.origin + '/api/interview/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return await resp.json();
}

async function callInterviewEvaluate(question, userAnswer) {
  var payload = {
    company: chatCompany,
    role: chatRole,
    question: question,
    user_answer: userAnswer
  };

  var resp = await fetch(window.location.origin + '/api/interview/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return await resp.json();
}

function scoreBar(score) {
  var pct = (score / 10) * 100;
  var color = score >= 8 ? '#10b981' : (score >= 5 ? '#f59e0b' : '#ef4444');
  return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <div style="flex:1;background:rgba(255,255,255,0.06);border-radius:99px;height:6px;">
      <div style="width:${pct}%;background:${color};height:6px;border-radius:99px;transition:width 0.6s;"></div>
    </div>
    <span style="font-size:0.8rem;font-weight:700;color:${color};min-width:28px;text-align:right;">${score}/10</span>
  </div>`;
}

function addEvaluationCard(evalData) {
  var messages = document.getElementById('chatMessages');
  var card = document.createElement('div');
  card.className = 'eval-card';
  var overall = evalData.overall_score || Math.round(((evalData.technical_accuracy||evalData.technical_score||5)+(evalData.problem_solving||5)+(evalData.communication_clarity||evalData.clarity_score||5)+(evalData.system_thinking||5)+(evalData.confidence||5))/5);
  var overallColor = overall >= 8 ? '#10b981' : (overall >= 5 ? '#f59e0b' : '#ef4444');
  var strengthsHtml = (evalData.strengths||[]).map(s=>`<li style="color:#86efac;margin-bottom:2px">✓ ${s}</li>`).join('');
  var weaknessHtml = (evalData.weaknesses||[]).map(w=>`<li style="color:#fca5a5;margin-bottom:2px">✕ ${w}</li>`).join('');
  card.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <div style="font-size:0.85rem;font-weight:700;color:#cbd5e1;text-transform:uppercase;letter-spacing:1px;">📊 Answer Evaluation</div>
      <div style="background:${overallColor};color:#000;padding:2px 10px;border-radius:99px;font-size:0.85rem;font-weight:800;">Overall: ${overall}/10</div>
    </div>
    <div style="margin-bottom:10px;">
      <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">Technical Accuracy</div>
      ${scoreBar(evalData.technical_accuracy||evalData.technical_score||5)}
      <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">Problem Solving</div>
      ${scoreBar(evalData.problem_solving||5)}
      <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">Communication</div>
      ${scoreBar(evalData.communication_clarity||evalData.clarity_score||5)}
      <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">System Thinking</div>
      ${scoreBar(evalData.system_thinking||5)}
      <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">Confidence</div>
      ${scoreBar(evalData.confidence||5)}
    </div>
    ${strengthsHtml ? `<div style="display:flex;gap:16px;margin-bottom:10px;">
      <div style="flex:1;"><div style="font-size:0.75rem;font-weight:700;color:#86efac;margin-bottom:4px;">✅ Strengths</div><ul style="list-style:none;padding:0;font-size:0.8rem;">${strengthsHtml}</ul></div>
      <div style="flex:1;"><div style="font-size:0.75rem;font-weight:700;color:#fca5a5;margin-bottom:4px;">⚠️ Improve</div><ul style="list-style:none;padding:0;font-size:0.8rem;">${weaknessHtml}</ul></div>
    </div>` : ''}
    <div style="font-size:0.85rem;color:#f8fafc;background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;border-left:3px solid #3b82f6;">
      <strong>💡 Feedback:</strong> ${evalData.feedback||'Good effort! Keep it up.'}
    </div>
  `;
  messages.appendChild(card);
  messages.scrollTop = messages.scrollHeight;
}

async function sendChatAnswer() {
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('chatSendBtn');
  var answer = input.value.trim();

  if (!answer) {
    input.focus();
    return;
  }

  var lastAiQuestion = '';
  for (var i = chatHistory.length - 1; i >= 0; i--) {
    if (chatHistory[i].role === 'ai') {
      lastAiQuestion = chatHistory[i].content;
      break;
    }
  }

  // Show user's answer
  chatHistory.push({ role: 'user', content: answer });
  addChatBubble('user', answer, null);
  input.value = '';
  input.disabled = true;
  sendBtn.disabled = true;

  showTypingIndicator();

  try {
    var askPromise = callInterviewAPI(answer);
    var evalPromise = callInterviewEvaluate(lastAiQuestion, answer);

    var [data, evalData] = await Promise.all([askPromise, evalPromise]);

    removeTypingIndicator();

    if (evalData && (evalData.technical_score !== undefined || evalData.technical_accuracy !== undefined)) {
      addEvaluationCard(evalData);
      sessionEvaluations.push(evalData);

      // Adaptive difficulty
      var overall = evalData.overall_score || Math.round(((evalData.technical_accuracy||evalData.technical_score||5)+(evalData.problem_solving||5)+(evalData.communication_clarity||evalData.clarity_score||5)+(evalData.system_thinking||5)+(evalData.confidence||5))/5);
      var prevDiff = currentDifficulty;
      if (overall >= 8) {
        if (currentDifficulty === 'easy') currentDifficulty = 'medium';
        else if (currentDifficulty === 'medium') currentDifficulty = 'hard';
      } else if (overall <= 4) {
        if (currentDifficulty === 'hard') currentDifficulty = 'medium';
        else if (currentDifficulty === 'medium') currentDifficulty = 'easy';
      }
      if (prevDiff !== currentDifficulty) syncDifficultyToDB();
    }

    chatHistory.push({ role: 'ai', content: data.next_question });
    addChatBubble('ai', data.next_question, data.question_type);

    if (data.question_type === 'coding') {
      showCodingEnvironment(data.next_question);
    }

    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  } catch (e) {
    removeTypingIndicator();
    input.disabled = false;
    sendBtn.disabled = false;
    showToast('Error', 'AI response failed: ' + e.message, true);
  }
}

async function syncDifficultyToDB() {
  try {
    await fetch(window.location.origin + '/api/interview/update_difficulty', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company: chatCompany,
        role: chatRole,
        difficulty: currentDifficulty
      })
    });
  } catch (e) {
    console.warn('Could not sync difficulty:', e);
  }
}

// Current coding problem state
var currentProblem = '';
var currentProblemData = null; // Full problem object with test_cases, hints etc.
var editor = null;

async function submitCode() {
    var btn = document.getElementById('runCodeBtn');
    var resultDiv = document.getElementById('codingResult');
    var code = editor ? editor.getValue() : document.getElementById('codeTextarea')?.value || '';

    if (!code.trim() || code.includes('# Write your Python')) {
        showToast('Empty Code', 'Please write your solution before running.', true);
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '⏳ Running Tests...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div style="color:#94a3b8;font-size:0.9rem;padding:12px;">🔄 Executing code against test cases...</div>';

    var testCases = (currentProblemData && currentProblemData.test_cases) || [];

    try {
        // Step 1: Execute code via Judge0
        var execResp = await fetch(window.location.origin + '/api/interview/execute_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code, language: 'python', test_cases: testCases, problem: currentProblem })
        });
        var execData = await execResp.json();

        // Show test case results
        showTestResults(execData);
        sessionCodingScore = execData.passed_pct || 0;

        // Step 2: Get AI code review
        btn.innerHTML = '🔍 Getting AI Review...';
        var reviewResp = await fetch(window.location.origin + '/api/interview/code_review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ problem: currentProblem, code: code, execution_results: execData })
        });
        var reviewData = await reviewResp.json();
        showCodeReview(reviewData);

    } catch (e) {
        resultDiv.innerHTML = '<div style="color:#ef4444;padding:12px;">⚠️ Evaluation error: ' + e.message + '</div>';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '▶ Run Code';
    }
}

function showTestResults(execData) {
    var resultDiv = document.getElementById('codingResult');
    var results = execData.results || [];
    var passed = execData.passed || 0;
    var total = execData.total || results.length;
    var pct = execData.passed_pct || 0;
    var barColor = pct >= 80 ? '#10b981' : (pct >= 50 ? '#f59e0b' : '#ef4444');

    var rows = results.map(r => `
      <div style="display:flex;align-items:flex-start;gap:10px;padding:8px;background:rgba(0,0,0,0.15);border-radius:6px;margin-bottom:6px;border-left:3px solid ${r.passed?'#10b981':'#ef4444'};">
        <span style="font-size:1rem;">${r.passed?'✅':'❌'}</span>
        <div style="flex:1;font-size:0.8rem;">
          <div style="color:#94a3b8;">Test ${r.test_num}: <code style="color:#e2e8f0;">${r.input?.replace(/\n/g,' | ')||'N/A'}</code></div>
          ${!r.passed && r.actual ? `<div style="color:#fca5a5;">Got: <code>${r.actual}</code> | Expected: <code>${r.expected}</code></div>` : ''}
          ${r.simulated ? '<div style="color:#64748b;font-size:0.7rem;">(simulated)</div>' : ''}
        </div>
      </div>`).join('');

    resultDiv.innerHTML = `
      <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(124,58,237,0.2);border-radius:12px;padding:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div style="font-weight:700;color:#f8fafc;font-size:1rem;">Test Results</div>
          <div style="font-weight:800;color:${barColor};font-size:1.1rem;">${passed}/${total} Passed</div>
        </div>
        <div style="background:rgba(0,0,0,0.2);border-radius:99px;height:8px;margin-bottom:14px;">
          <div style="width:${pct}%;background:${barColor};height:8px;border-radius:99px;transition:width 0.8s;"></div>
        </div>
        ${rows}
        ${execData.execution_time ? `<div style="font-size:0.75rem;color:#64748b;margin-top:8px;">⏱ Execution time: ${execData.execution_time}</div>` : ''}
      </div>`;
    resultDiv.style.display = 'block';
}

function showCodeReview(reviewData) {
    var reviewDiv = document.getElementById('codeReviewSection');
    if (!reviewDiv) {
        reviewDiv = document.createElement('div');
        reviewDiv.id = 'codeReviewSection';
        reviewDiv.style.marginTop = '12px';
        document.getElementById('codingResult').parentNode.appendChild(reviewDiv);
    }
    var strengths = (reviewData.strengths||[]).map(s=>`<li style="color:#86efac;">✓ ${s}</li>`).join('');
    var improvements = (reviewData.improvements||[]).map(i=>`<li style="color:#fca5a5;">→ ${i}</li>`).join('');
    var quality = (reviewData.code_quality_notes||[]).map(n=>`<li style="color:#93c5fd;">${n}</li>`).join('');
    var rating = reviewData.overall_rating || 7;
    var ratingColor = rating >= 8 ? '#10b981' : (rating >= 5 ? '#f59e0b' : '#ef4444');
    reviewDiv.innerHTML = `
      <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(6,182,212,0.2);border-radius:12px;padding:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div style="font-weight:700;color:#06b6d4;font-size:0.9rem;text-transform:uppercase;letter-spacing:1px;">🤖 AI Code Review</div>
          <div style="background:${ratingColor};color:#000;padding:2px 10px;border-radius:99px;font-weight:800;font-size:0.85rem;">${rating}/10</div>
        </div>
        <div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
          <div style="background:rgba(0,0,0,0.2);padding:6px 12px;border-radius:6px;font-size:0.8rem;">⏱ Time: <strong style="color:#3b82f6;">${reviewData.time_complexity||'N/A'}</strong></div>
          <div style="background:rgba(0,0,0,0.2);padding:6px 12px;border-radius:6px;font-size:0.8rem;">💾 Space: <strong style="color:#8b5cf6;">${reviewData.space_complexity||'N/A'}</strong></div>
        </div>
        <div style="display:flex;gap:16px;margin-bottom:12px;">
          <div style="flex:1;"><div style="font-size:0.75rem;font-weight:700;color:#86efac;margin-bottom:4px;">Strengths</div><ul style="list-style:none;padding:0;font-size:0.8rem;">${strengths}</ul></div>
          <div style="flex:1;"><div style="font-size:0.75rem;font-weight:700;color:#fca5a5;margin-bottom:4px;">Improvements</div><ul style="list-style:none;padding:0;font-size:0.8rem;">${improvements}</ul></div>
        </div>
        ${quality ? `<div style="font-size:0.75rem;font-weight:700;color:#93c5fd;margin-bottom:4px;">Code Quality</div><ul style="list-style:none;padding:0;font-size:0.8rem;">${quality}</ul>` : ''}
        ${reviewData.optimized_approach ? `<div style="font-size:0.85rem;color:#f8fafc;background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;border-left:3px solid #06b6d4;margin-top:8px;"><strong>💡 Optimal Approach:</strong> ${reviewData.optimized_approach}</div>` : ''}
      </div>`;
    reviewDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function startAIInterview() {
  var startBtn = document.getElementById('chatStartBtn');
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('chatSendBtn');

  startBtn.disabled = true;
  startBtn.innerHTML = '⏳ Connecting to AI Interviewer...';

  showTypingIndicator();

  try {
    var data = await callInterviewAPI(null);
    removeTypingIndicator();

    chatHistory.push({ role: 'ai', content: data.next_question });
    addChatBubble('ai', data.next_question, data.question_type);

    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
    startBtn.style.display = 'none';

    if (data.question_type === 'coding') {
      showCodingEnvironment(data.next_question);
    }
  } catch (e) {
    removeTypingIndicator();
    startBtn.disabled = false;
    startBtn.innerHTML = '🚀 Start AI Interview';
    showToast('Connection Error', 'Could not reach AI interviewer: ' + e.message, true);
  }
}

function showCodingEnvironment(problemText) {
    var chatSection = document.getElementById('aiChatSection') || document.querySelector('.chat-messages')?.parentNode;
    var codingArea = document.getElementById('codingAreaMain');
    if (!codingArea) {
        codingArea = document.createElement('div');
        codingArea.id = 'codingAreaMain';
        codingArea.style.cssText = 'margin-top:24px;border:1px solid rgba(16,185,129,0.2);border-radius:16px;overflow:hidden;background:rgba(0,0,0,0.2);';
        chatSection && chatSection.parentNode.insertBefore(codingArea, chatSection.nextSibling);
    }

    var tc = (currentProblemData && currentProblemData.test_cases) || [];
    var tcHtml = tc.slice(0,2).map((t,i)=>``).join('');
    var hintsArr = (currentProblemData && currentProblemData.hints) || ['Think carefully about the data structure.', 'Consider time vs space trade-offs.', 'Can you solve it in one pass?'];
    var hintBtns = hintsArr.map((h,i)=>`<button onclick="revealHint(${i},this,'${h.replace(/'/g,"\'")}')" style="background:rgba(245,158,11,0.1);color:#fbbf24;border:1px solid rgba(245,158,11,0.3);padding:6px 12px;border-radius:6px;font-size:0.8rem;cursor:pointer;margin-right:6px;">Hint ${i+1}</button>`).join('');
    var starterCode = (currentProblemData && currentProblemData.starter_code) || `# Write your Python solution here
def solution():
    pass`;
    var title = (currentProblemData && currentProblemData.title) || 'Coding Challenge';
    var constraints = (currentProblemData && currentProblemData.constraints) || '';
    var examples = (currentProblemData && currentProblemData.examples) || [];
    var exHtml = examples.slice(0,1).map(ex=>`<div style="background:rgba(0,0,0,0.2);border-radius:6px;padding:8px;font-size:0.8rem;font-family:'Fira Code',monospace;"><span style="color:#94a3b8;">Input:</span> <span style="color:#e2e8f0;">${ex.input||''}</span><br><span style="color:#94a3b8;">Output:</span> <span style="color:#10b981;">${ex.output||''}</span>${ex.explanation?`<br><span style="color:#64748b;">// ${ex.explanation}</span>`:''}</div>`).join('');

    codingArea.innerHTML = `
      <div style="background:rgba(16,185,129,0.05);border-bottom:1px solid rgba(16,185,129,0.15);padding:14px 20px;display:flex;align-items:center;justify-content:space-between;">
        <div style="font-family:'Outfit';font-size:1rem;font-weight:700;color:#10b981;">💻 ${title}</div>
        <div style="display:flex;gap:6px;align-items:center;">
          <span style="background:rgba(124,58,237,0.15);color:#a78bfa;padding:3px 10px;border-radius:99px;font-size:0.75rem;font-weight:600;">${currentDifficulty.toUpperCase()}</span>
          <button onclick="document.getElementById('codingAreaMain').style.display='none'" style="background:rgba(239,68,68,0.1);color:#f87171;border:1px solid rgba(239,68,68,0.2);padding:4px 10px;border-radius:6px;font-size:0.8rem;cursor:pointer;">✕ Close</button>
        </div>
      </div>
      <div style="padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);">
        <p style="color:#e2e8f0;font-size:0.9rem;line-height:1.7;margin-bottom:10px;">${problemText}</p>
        ${constraints ? `<div style="font-size:0.8rem;color:#64748b;margin-bottom:10px;">Constraints: ${constraints}</div>` : ''}
        ${exHtml}
        <div style="margin-top:12px;">${hintBtns}<button onclick="revealHint(3,this,'${((currentProblemData&&currentProblemData.solution_approach)||'Break the problem into smaller steps.').replace(/'/g,"\'")}'" style="background:rgba(139,92,246,0.1);color:#a78bfa;border:1px solid rgba(139,92,246,0.3);padding:6px 12px;border-radius:6px;font-size:0.8rem;cursor:pointer;">💡 Solution Approach</button></div>
        <div id="hintDisplay" style="margin-top:10px;display:none;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:8px;padding:10px;font-size:0.85rem;color:#fcd34d;"></div>
      </div>
      <div id="monacoEditorWrap" style="height:300px;border-bottom:1px solid rgba(255,255,255,0.05);position:relative;">
        <div id="monacoEditor" style="height:100%;"></div>
        <textarea id="codeTextarea" style="display:none;width:100%;height:100%;background:#1e1e1e;color:#d4d4d4;border:none;padding:14px;font-family:'Fira Code',monospace;font-size:13px;resize:none;outline:none;">${starterCode}</textarea>
      </div>
      <div style="padding:12px 16px;display:flex;gap:10px;align-items:center;">
        <button id="runCodeBtn" onclick="submitCode()" style="background:#10b981;color:white;border:none;padding:10px 24px;border-radius:8px;font-weight:700;cursor:pointer;flex:1;font-size:0.9rem;">▶ Run Code</button>
        <select id="langSelect" style="background:rgba(255,255,255,0.05);color:#94a3b8;border:1px solid rgba(255,255,255,0.1);padding:8px 12px;border-radius:8px;font-size:0.85rem;"><option value="python">Python</option><option value="javascript">JavaScript</option></select>
      </div>
      <div id="codingResult" style="padding:0 16px 16px;display:none;"></div>
    `;
    codingArea.style.display = 'block';
    currentProblem = problemText;

    // Init Monaco or fallback textarea
    if (typeof require !== 'undefined') {
        initMonaco(starterCode);
    } else {
        var loader = document.createElement('script');
        loader.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs/loader.min.js';
        loader.onload = () => initMonaco(starterCode);
        loader.onerror = () => { document.getElementById('codeTextarea').style.display='block'; document.getElementById('monacoEditor').style.display='none'; };
        document.head.appendChild(loader);
    }
}

function initMonaco(starterCode) {
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs' } });
    require(['vs/editor/editor.main'], function() {
        editor = monaco.editor.create(document.getElementById('monacoEditor'), {
            value: starterCode || `# Write your Python solution here
def solution():
    pass`,
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            roundedSelection: true,
            scrollBeyondLastLine: false,
            cursorStyle: 'line'
        });
    });
}

function revealHint(idx, btn, hintText) {
    var display = document.getElementById('hintDisplay');
    if (display) {
        display.style.display = 'block';
        var labels = ['Hint 1', 'Hint 2', 'Hint 3', '💡 Solution Approach'];
        display.innerHTML = `<strong style="color:#fbbf24;">${labels[Math.min(idx,3)]}: </strong>${hintText}`;
    }
    btn.style.opacity = '0.5';
    btn.disabled = true;
}

async function generateFinalReport() {
    var btn = document.getElementById('endSessionBtn');
    if (btn) { btn.disabled=true; btn.innerHTML='⏳ Generating Report...'; }

    try {
        var resp = await fetch(window.location.origin + '/api/interview/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company: chatCompany,
                role: chatRole,
                evaluations: sessionEvaluations,
                coding_score: sessionCodingScore
            })
        });
        var report = await resp.json();
        showFinalReportModal(report);
    } catch(e) {
        showToast('Error', 'Could not generate report: ' + e.message, true);
    } finally {
        if (btn) { btn.disabled=false; btn.innerHTML='📊 Final Report'; }
    }
}

function showFinalReportModal(report) {
    var modal = document.getElementById('reportModal');
    if (!modal) return;
    var metrics = report.metrics || {};
    var recs = (report.recommendations || []).map(r=>`<li style="margin-bottom:6px;color:#e2e8f0;">→ ${r}</li>`).join('');
    var strengths = (report.top_strengths || []).map(s=>`<li style="color:#86efac;margin-bottom:4px;">✓ ${s}</li>`).join('');
    var weaknesses = (report.top_weaknesses || []).map(w=>`<li style="color:#fca5a5;margin-bottom:4px;">✕ ${w}</li>`).join('');
    var overall = report.overall_score || 70;
    var verdict = report.verdict || 'Candidate Evaluated';
    var verdictColor = report.verdict_color || '#06b6d4';

    function metricRow(label, val) {
        var color = val>=80?'#10b981':(val>=60?'#f59e0b':'#ef4444');
        return `<div style="margin-bottom:10px;"><div style="display:flex;justify-content:space-between;margin-bottom:4px;"><span style="color:#94a3b8;font-size:0.85rem;">${label}</span><span style="color:${color};font-weight:700;">${val}/100</span></div><div style="background:rgba(255,255,255,0.06);border-radius:99px;height:6px;"><div style="width:${val}%;background:${color};height:6px;border-radius:99px;transition:width 1s;"></div></div></div>`;
    }

    modal.querySelector('#reportContent').innerHTML = `
      <div style="text-align:center;margin-bottom:24px;">
        <div style="font-size:3rem;font-weight:800;color:${verdictColor};">${overall}</div>
        <div style="font-size:0.85rem;color:#94a3b8;">Overall Score</div>
        <div style="margin-top:8px;font-size:1.1rem;font-weight:700;color:${verdictColor};">${verdict}</div>
        <div style="font-size:0.8rem;color:#64748b;margin-top:2px;">${report.role} @ ${report.company} · ${report.total_questions||0} questions evaluated</div>
      </div>
      <div style="margin-bottom:20px;">
        ${metricRow('Technical Knowledge', metrics.technical_knowledge||70)}
        ${metricRow('Problem Solving', metrics.problem_solving||70)}
        ${metricRow('Communication', metrics.communication||70)}
        ${metricRow('System Thinking', metrics.system_thinking||60)}
        ${metricRow('Confidence', metrics.confidence||65)}
        ${metricRow('Coding Ability', metrics.coding_ability||70)}
      </div>
      <div style="display:flex;gap:16px;margin-bottom:20px;">
        ${strengths?`<div style="flex:1;"><div style="font-size:0.75rem;font-weight:700;color:#86efac;margin-bottom:6px;text-transform:uppercase;">✅ Top Strengths</div><ul style="list-style:none;padding:0;font-size:0.82rem;">${strengths}</ul></div>`:''}
        ${weaknesses?`<div style="flex:1;"><div style="font-size:0.75rem;font-weight:700;color:#fca5a5;margin-bottom:6px;text-transform:uppercase;">⚠️ Improve</div><ul style="list-style:none;padding:0;font-size:0.82rem;">${weaknesses}</ul></div>`:''}
      </div>
      ${recs?`<div style="border-top:1px solid rgba(255,255,255,0.08);padding-top:16px;"><div style="font-size:0.85rem;font-weight:700;color:#f8fafc;margin-bottom:8px;">📚 Recommended Topics to Improve</div><ul style="padding-left:0;list-style:none;font-size:0.85rem;">${recs}</ul></div>`:''}
    `;
    modal.style.display = 'flex';
}

function showTranscript() {
    var panel = document.getElementById('transcriptPanel');
    if (!panel) return;
    var html = chatHistory.map((msg,i) => {
        var isAI = msg.role === 'ai';
        return `<div style="margin-bottom:12px;padding:10px 14px;background:${isAI?'rgba(124,58,237,0.08)':'rgba(6,182,212,0.05)'};border-radius:8px;border-left:3px solid ${isAI?'#7c3aed':'#06b6d4'};">
          <div style="font-size:0.75rem;font-weight:600;color:${isAI?'#a78bfa':'#22d3ee'};margin-bottom:4px;">${isAI?'🤖 AI Interviewer':'👤 You'}</div>
          <div style="font-size:0.88rem;color:#e2e8f0;line-height:1.5;">${msg.content}</div>
        </div>`;
    }).join('');
    panel.innerHTML = html || '<div style="color:#64748b;text-align:center;padding:20px;">No conversation yet.</div>';
    panel.closest('[id^=transcriptModal]') && (panel.closest('[id^=transcriptModal]').style.display = 'flex');
    var transcriptModal = document.getElementById('transcriptModal');
    if (transcriptModal) transcriptModal.style.display = 'flex';
}

// Allow Enter to submit (Shift+Enter for new line)
document.addEventListener('DOMContentLoaded', function() {
  var chatInput = document.getElementById('chatInput');
  if (chatInput) {
    chatInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatAnswer();
      }
    });
  }
  // Wire End Session button
  var endBtn = document.getElementById('endSessionBtn');
  if (endBtn) endBtn.addEventListener('click', generateFinalReport);
  // Wire Transcript button
  var txBtn = document.getElementById('transcriptBtn');
  if (txBtn) txBtn.addEventListener('click', showTranscript);
});
