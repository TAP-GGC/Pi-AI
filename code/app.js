// ---------------- TIMER ELEMENTS ----------------
const start = document.getElementById("start");
const stop = document.getElementById("stop");
const reset = document.getElementById("reset");
const timer = document.getElementById("timer");
const clockRingImage = document.getElementById("clock-ring"); 
const speechBubble = document.getElementById("speechBubble");


// ---------------- TIMER LOGIC ----------------
let customTime = 0; // default 25:00
let timeLeft = customTime;
let interval;

const updateTimer = () => {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    timer.textContent = `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
};

// Start Timer
const startTimer = () => {
    if (interval) return;

    interval = setInterval(() => {
        timeLeft--;
        updateTimer();

        if (timeLeft === 0) {
            clearInterval(interval);

            // Show clock image and add shake animation
            clockRingImage.style.visibility = "visible";
            clockRingImage.classList.add("shake");

            // Optional: play alarm sound
            const audio = new Audio("sounds/alarm.mp3"); // put your sound here
            audio.play();

            //alert("Time's up!");

            // Reset timer
            timeLeft = customTime;
            updateTimer();

            // Hide clock and stop shake after 5 seconds
            setTimeout(() => {
                clockRingImage.style.visibility = "hidden";
                clockRingImage.classList.remove("shake");
            }, 5000);
        }
    }, 1000);
};

// Stop Timer
const stopTimer = () => {
    clearInterval(interval);
    interval = null;
};

// Reset Timer
const resetTimer = () => {
    clearInterval(interval);
    interval = null;
    timeLeft = customTime;
    updateTimer();

    // Hide clock if visible
    if (clockRingImage) {
    clockRingImage.style.visibility = "hidden";
    clockRingImage.classList.remove("shake");
    }
};

// Event listeners
start.addEventListener("click", startTimer);
stop.addEventListener("click", stopTimer);
reset.addEventListener("click", resetTimer);


// ---------------- EDITABLE TIMER ----------------
timer.setAttribute("contenteditable", "true");

// Input formatting while typing
timer.addEventListener("input", () => {
    timer.textContent = timer.textContent.replace(/[^\d:]/g, ""); // only numbers & colon
    const text = timer.textContent.replace(":", "");
    if (text.length >= 3) {
        let minutes = text.slice(0, text.length - 2);
        let seconds = text.slice(-2);
        timer.textContent = `${minutes}:${seconds}`;
        placeCaretAtEnd(timer);
    }
});

// When finished editing (blur event)
timer.addEventListener("blur", () => {
    const timeText = timer.textContent.trim();
    const parts = timeText.split(":");

    let minutes = 0;
    let seconds = 0;

    if (parts.length === 2) {
        minutes = parseInt(parts[0]);
        seconds = parseInt(parts[1]);
    } else if (parts.length === 1) {
        minutes = parseInt(parts[0]);
        seconds = 0;
    }

    if (!isNaN(minutes) && !isNaN(seconds)) {
        customTime = (minutes * 60) + seconds;
        timeLeft = customTime;
        updateTimer();
    } else {
        updateTimer(); // reset if invalid
    }
});

// Helper function to keep cursor at end
function placeCaretAtEnd(el) {
    el.focus();
    if (typeof window.getSelection != "undefined"
        && typeof document.createRange != "undefined") {
        const range = document.createRange();
        range.selectNodeContents(el);
        range.collapse(false);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
}


// ---------------- STUDY PLAN CODE ----------------
const API_URL = '/api/chat';
const PLAN_STORAGE_KEY = 'piAI_studyPlan';
let studyTopics = [];

function savePlan() {
    localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(studyTopics));
}

function updateProgress() {
    const total = studyTopics.length;
    const done = studyTopics.filter(t => t.done).length;
    document.getElementById('progress-label').textContent = `${done} / ${total} topics complete`;
    const pct = total === 0 ? 0 : Math.round((done / total) * 100);
    document.getElementById('progress-bar-fill').style.width = pct + '%';
}

function checkCompletion() {
    const msg = document.getElementById('plan-complete-msg');
    if (studyTopics.length > 0 && studyTopics.every(t => t.done)) {
        msg.style.display = 'block';
    } else {
        msg.style.display = 'none';
    }
}

function renderTopics() {
    const list = document.getElementById('topic-list');
    list.innerHTML = '';
    studyTopics.forEach((topic, i) => {
        const isLocked = !topic.done && studyTopics.slice(0, i).some(t => !t.done);
        const li = document.createElement('li');
        li.className = 'topic-item' +
            (topic.done ? ' completed' : '') +
            (isLocked   ? ' locked'    : '');
        li.dataset.index = i;

        const statusIcon = topic.done
            ? '<span class="topic-status">✓</span>'
            : isLocked
                ? '<span class="topic-status">🔒</span>'
                : '<span class="topic-status pending"></span>';

        li.innerHTML = `
            ${statusIcon}
            <span class="topic-text">${topic.text}</span>
            <button class="delete-topic-btn" data-index="${i}" title="Remove">✕</button>
        `;
        list.appendChild(li);
    });
    updateProgress();
    checkCompletion();
    document.getElementById('study-plan-area').style.display = 'block';
}

// Topic list — single unified click handler
document.getElementById('topic-list').addEventListener('click', function(e) {
    if (e.target.classList.contains('delete-topic-btn')) {
        const i = parseInt(e.target.dataset.index);
        studyTopics.splice(i, 1);
        savePlan();
        if (studyTopics.length === 0) {
            document.getElementById('study-plan-area').style.display = 'none';
        } else {
            renderTopics();
        }
        return;
    }
    const li = e.target.closest('.topic-item');
    if (!li) return;
    const i = parseInt(li.dataset.index);
    if (li.classList.contains('locked')) return;
    if (studyTopics[i].done) {
        studyTopics[i].done = false;
        savePlan();
        renderTopics();
        return;
    }
    openQuizModal(i);
});

// Manual add topic
document.getElementById('add-topic-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const input = document.getElementById('topic-input');
    const text = input.value.trim();
    if (text) {
        studyTopics.push({ text, done: false });
        savePlan();
        renderTopics();
        input.value = '';
    }
});

// Load saved plan on page load
const savedPlan = localStorage.getItem(PLAN_STORAGE_KEY);
if (savedPlan) {
    studyTopics = JSON.parse(savedPlan);
    if (studyTopics.length > 0) renderTopics();
}

// ---------------- QUIZ MODAL ----------------
let quizTopicIndex = null;
let quizData = null;
const OPTION_LABELS = ['A', 'B', 'C', 'D'];

async function openQuizModal(topicIndex) {
    quizTopicIndex = topicIndex;
    quizData = null;
    const topic = studyTopics[topicIndex].text;

    document.getElementById('quiz-topic-label').textContent = topic;
    document.getElementById('quiz-loading').style.display = 'flex';
    document.getElementById('quiz-explanation').style.display = 'none';
    document.getElementById('quiz-q1-wrap').style.display = 'none';
    document.getElementById('quiz-q2-wrap').style.display = 'none';
    document.getElementById('quiz-feedback-1').style.display = 'none';
    document.getElementById('quiz-feedback-2').style.display = 'none';
    document.getElementById('quiz-options-1').innerHTML = '';
    document.getElementById('quiz-options-2').innerHTML = '';
    document.getElementById('quiz-overlay').style.display = 'flex';

    try {
        const res = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `For the topic "${topic}": write a short 2-3 sentence beginner-friendly explanation, then create exactly 2 multiple choice questions based only on that explanation. Each question must have exactly 4 options. Return ONLY valid JSON in this format, no extra text or markdown: {"explanation":"...","questions":[{"text":"...","options":["...","...","...","..."],"correct":0},{"text":"...","options":["...","...","...","..."],"correct":2}]} where "correct" is the 0-based index of the correct option.`,
                history: []
            })
        });
        const data = await res.json();
        if (data.response) {
            const jsonMatch = data.response.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                quizData = JSON.parse(jsonMatch[0]);
                document.getElementById('quiz-loading').style.display = 'none';
                document.getElementById('quiz-explanation').textContent = quizData.explanation;
                document.getElementById('quiz-explanation').style.display = 'block';
                renderQuestion(1);
            }
        }
    } catch {
        document.getElementById('quiz-loading').textContent = 'Could not connect to Pi. Try skipping.';
    }
}

function renderQuestion(step) {
    const q = quizData.questions[step - 1];
    document.getElementById(`quiz-q${step}-text`).textContent = q.text;
    const optionsEl = document.getElementById(`quiz-options-${step}`);
    optionsEl.innerHTML = '';
    q.options.forEach((opt, i) => {
        const btn = document.createElement('button');
        btn.className = 'quiz-option-btn';
        btn.innerHTML = `<span class="option-label">${OPTION_LABELS[i]}</span>${opt}`;
        btn.addEventListener('click', () => selectOption(step, i));
        optionsEl.appendChild(btn);
    });
    document.getElementById(`quiz-q${step}-wrap`).style.display = 'block';
    if (step === 2) {
        document.getElementById('quiz-q2-wrap').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function selectOption(step, selectedIndex) {
    const q = quizData.questions[step - 1];
    const optionsEl = document.getElementById(`quiz-options-${step}`);
    const feedbackEl = document.getElementById(`quiz-feedback-${step}`);
    const isCorrect = selectedIndex === q.correct;

    Array.from(optionsEl.querySelectorAll('.quiz-option-btn')).forEach((btn, i) => {
        btn.disabled = true;
        if (i === q.correct) btn.classList.add('option-correct');
        else if (i === selectedIndex && !isCorrect) btn.classList.add('option-wrong');
    });

    feedbackEl.textContent = isCorrect ? 'Correct! Nice work!' : `Not quite — the right answer is ${OPTION_LABELS[q.correct]}.`;
    feedbackEl.className = isCorrect ? 'quiz-correct' : 'quiz-incorrect';
    feedbackEl.style.display = 'block';

    if (isCorrect) {
        if (step === 1) {
            setTimeout(() => renderQuestion(2), 1200);
        } else {
            setTimeout(() => {
                const idx = quizTopicIndex;
                closeQuizModal();
                studyTopics[idx].done = true;
                savePlan();
                renderTopics();
            }, 1500);
        }
    } else {
        setTimeout(() => {
            feedbackEl.style.display = 'none';
            Array.from(optionsEl.querySelectorAll('.quiz-option-btn')).forEach(btn => {
                btn.disabled = false;
                btn.classList.remove('option-correct', 'option-wrong');
            });
        }, 1800);
    }
}

function closeQuizModal() {
    document.getElementById('quiz-overlay').style.display = 'none';
    quizTopicIndex = null;
    quizData = null;
}

document.getElementById('quiz-skip-btn').addEventListener('click', function() {
    const idx = quizTopicIndex;
    closeQuizModal();
    studyTopics[idx].done = true;
    savePlan();
    renderTopics();
});

document.getElementById('quiz-close-btn').addEventListener('click', closeQuizModal);

// ---------------- SPEECH BUBBLE MESSAGE ----------------
setTimeout(() => {
    if (speechBubble) {
        speechBubble.innerHTML = `
        Do you need assistance?<br><br>
        <button class="bubble-button" onclick="window.location.href='chatInterface.html'">
                Yes, please →
            </button>
        `;
    }
}, 3000);

