var app = {};

var chartDom = document.getElementById('count_and_tokens');
var myChart = echarts.init(chartDom);
var option;

// 生成X轴时间数据
const categories = (function () {
    let now = new Date();
    let res = [];
    let len = 10;
    while (len--) {
        res.unshift(now.toLocaleTimeString().replace(/^\D*/, ''));
        now = new Date(+now - 2000);
    }
    return res;
})();
// 生成X轴数字数据
const categories2 = (function () {
    let res = [];
    let len = 10;
    while (len--) {
        res.push(0);
    }
    return res;
})();
// 生成柱状图随机数据
const data = (function () {
    let res = [];
    let len = 10;
    while (len--) {
        res.push(0);
    }
    return res;
})();
// 生成折线图随机数据
const data2 = (function () {
    let res = [];
    let len = 0;
    while (len < 10) {
        res.push(+(Math.random() * 10 + 5).toFixed(1));
        len++;
    }
    return res;
})();

option = {
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'cross',
            label: {
                backgroundColor: '#0e85a9',
                color: '#ffffff'
            }
        },
        textStyle: { color: '#000000' }
    },
    legend: {
        textStyle: { color: '#ffffff' }
    },
    toolbox: {
        show: true,
        iconStyle: { color: '#ffffff' },
        feature: {
            dataView: { readOnly: false, textStyle: { color: '#ffffff' } },
            restore: { textStyle: { color: '#ffffff' } },
            saveAsImage: { textStyle: { color: '#ffffff' } }
        }
    },
    dataZoom: {
        show: false,
        start: 0,
        end: 100
    },
    xAxis: [
        {
            type: 'category',
            boundaryGap: true,
            data: categories,
            axisLine: { lineStyle: { color: '#ffffff' } },
            axisTick: { lineStyle: { color: '#ffffff' } },
            axisLabel: { color: '#ffffff' },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } }
        },
        {
            type: 'category',
            boundaryGap: true,
            data: categories2,
            axisLine: { lineStyle: { color: '#ffffff' } },
            axisTick: { lineStyle: { color: '#ffffff' } },
            axisLabel: { color: '#ffffff' },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } }
        }
    ],
    yAxis: [
        {
            type: 'value',
            scale: false, 
            name: 'tokens量',
            boundaryGap: [0.1, 0.1], 
            axisLine: { lineStyle: { color: '#ffffff' } },
            axisTick: { lineStyle: { color: '#ffffff' } },
            axisLabel: { color: '#ffffff' },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
            nameTextStyle: { color: '#ffffff' }
        },
        {
            type: 'value',
            scale: false, 
            name: '访问量',
            boundaryGap: [0.1, 0.1],
            axisLine: { lineStyle: { color: '#ffffff' } },
            axisTick: { lineStyle: { color: '#ffffff' } },
            axisLabel: { color: '#ffffff' },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
            nameTextStyle: { color: '#ffffff' }
        }
    ],
    series: [
        {
            name: '处理的访问次数(单位：次)',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: data,
            itemStyle: { color: 'rgba(15, 176, 163, 0.8)' }
        },
        {
            name: '处理的tokens量(单位：1000tokens)',
            type: 'line',
            data: data2,
            lineStyle: { color: '#054f25' },
            itemStyle: { color: '#0db851' },
            areaStyle: { color: 'rgba(255,255,255,0.2)' }
        }
    ],
};


// 定时更新数据（每2.1秒刷新一次）
app.count = 11;
setInterval(async function () {
    let axisData = new Date().toLocaleTimeString().replace(/^\D*/, '');
    // 移除第一个数据，新增随机数据（保持10个数据点）
    res = await fetch(`/api/counts_and_tokens`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
    });
    const result = await res.json();
    console.log(result);
    data.shift();
    data.push(result.total_counts);
    data2.shift();
    data2.push(result.total_tokens);
    categories.shift();
    categories.push(axisData);
    categories2.shift();
    categories2.push(app.count++);
    // 更新图表数据
    myChart.setOption({
        xAxis: [
            { data: categories },
            { data: categories2 }
        ],
        series: [
            { data: data },
            { data: data2 }
        ]
    });
}, 2100);

// 渲染图表
option && myChart.setOption(option);

// 可选：窗口大小变化时，自适应图表
window.addEventListener('resize', function() {
    myChart.resize();
});