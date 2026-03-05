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


// ---------------- TASK LIST CODE ----------------
const taskForm = document.getElementById("task-form");
const taskList = document.getElementById("task-list");
let taskIndex = 1;

taskForm.addEventListener("submit", function(event){
    event.preventDefault();

    const taskInput = document.getElementById("task-input");
    const taskText = taskInput.value.trim();

    if (taskText !== ""){
        const taskItem = document.createElement("li");
        taskItem.classList.add("task-item");
        taskItem.textContent = `${taskIndex}- ${taskText}`;
        
        taskItem.addEventListener("click", function () {
            this.classList.toggle("completed");
        });

        taskList.appendChild(taskItem);
        taskIndex++;
        taskInput.value = "";
    }

});

// ---------------- SPEECH BUBBLE MESSAGE ----------------
setTimeout(() => {
    if (speechBubble) {
        speechBubble.innerHTML = `
        <img src="images/whitebackgroundshuffle-pixilart.gif" class="brain" alt="Assist"><br>
      Do you need assistance?<br><br>
      <button class="bubble-button" onclick="window.location.href='chatInterface.html'">
        Yes, please →
      </button>
        `;
    }
}, 3000);
