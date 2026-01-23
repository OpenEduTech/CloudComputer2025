const digitalClock = document.getElementById('digital-clock');
const dateDisplay = document.getElementById('date-display');

// 日期格式化函数
function formatDate(date) {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    const weekday = weekdays[date.getDay()];
    return `${year} 年 ${month} 月 ${day} 日 ${weekday}`;
}

// 时间格式化函数
function formatTime(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${hours} : ${minutes} : ${seconds}`;
}

// 更新时钟显示
function updateClock() {
    const now = new Date();
    
    // 更新数字时钟
    digitalClock.textContent = formatTime(now);
    dateDisplay.textContent = formatDate(now);
}

// 初始化
updateClock();
setInterval(updateClock, 1000);