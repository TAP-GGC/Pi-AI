const start = document.getElementById("start");
const stop = document.getElementById("stop");
const reset = document.getElementById("reset");
const timer = document.getElementById("timer");

let customTime = 1500;
let timeLeft = customTime;
let interval;

const updateTimer = () => {
const minutes = Math.floor(timeLeft / 60);
const seconds = timeLeft % 60;

timer.innerHTML = `${minutes.toString().padStart(2, "0")}
:
${seconds.toString().padStart(2, "0")}`;
};

const startTimer = () => {
if (interval) return;

interval = setInterval(() => {
timeLeft--;
updateTimer();

if(timeLeft === 0){
clearInterval(interval);
alert("Time's up!");
timeLeft = customTime;
updateTimer();
}
}, 1000);
};

const stopTimer = () =>{
clearInterval(interval);
interval = null;

};

const resetTimer = () => {
clearInterval(interval);
interval = null;
timeLeft = customTime;
updateTimer();
};

start.addEventListener("click", startTimer);
stop.addEventListener("click", stopTimer);
reset.addEventListener("click", resetTimer);

const taskForm= document.getElementById("task-form");
const taskList= document.getElementById("task-list");

//Counter variable to track task index

let taskIndex = 1;

    //console.log(taskForm,taskList);

    taskForm.addEventListener("submit", function(event){
        event.preventDefault();
    
        const taskInput = document.getElementById("task-input");
        const taskText = taskInput.value.trim();

        //console.log(taskText);

        if (taskText !==""){
            //Creating new task item

            const taskItem = document.createElement("li");
            taskItem.classList.add("task-item");
            taskItem.textContent = `${taskIndex}- ${taskText}`;
        
        taskItem.addEventListener("click", function () {
            console.log("completed");
            this.classList.toggle("completed");
        });
        
            //append item to list
        taskList.appendChild(taskItem);


        //incrementing counter
        taskIndex++;

        taskInput.value = "";
        }
    });
