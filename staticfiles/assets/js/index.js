

$(function() {
    "use strict";

    // --- تبدیل عدد به فارسی ---
    function toPersianDigits(num) {
        return num.toString().replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
    }


    // --- گرفتن داده‌ها از عناصر HTML (که توی قالب جنگو گذاشتی) ---
    //const dailyLabels = JSON.parse(document.getElementById("daily-labels").textContent);
    //const dailyData = JSON.parse(document.getElementById("daily-data").textContent);

    //const weeklyLabels = JSON.parse(document.getElementById("weekly-labels").textContent);
    //const weeklyData = JSON.parse(document.getElementById("weekly-data").textContent);

     // ---- 📦 دریافت داده‌ها از تگ‌های JSON ----
    const dailyLabels = JSON.parse(document.getElementById("dailyLabels").textContent);
    const dailyData = JSON.parse(document.getElementById("dailyData").textContent);
    const weeklyLabels = JSON.parse(document.getElementById("weekLabels").textContent);
    const weeklyData = JSON.parse(document.getElementById("weekData").textContent);

    console.log("📊 Daily Labels:", dailyLabels);
    console.log("📊 Daily Data:", dailyData);
    console.log("📊 Weekly Labels:", weeklyLabels);
    console.log("📊 Weekly Data:", weeklyData);

    // chart 1: 🔹 نمودار میله‌ای فروش روزانه 30 روز اخیر
    var ctx1 = document.getElementById('chart1').getContext('2d');
    var myChart1 = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: dailyLabels,
            datasets: [{
                label: 'فروش روزانه',
                data: dailyData,
                backgroundColor: '#fff',
						borderColor: "transparent",
						pointRadius :"0",
						borderWidth: 3
            }]
        },
        options: {
            maintainAspectRatio: false,
            legend: {
                display: false,
                labels: {
                    fontColor: '#ddd',
                    boxWidth: 40
                }

            },
            tooltips: {
                callbacks: {
                    label: function (tooltipItem) {
                        const val = tooltipItem.raw.toLocaleString();
                        return toPersianDigits(val) + ' تومان';
                    }
                }
            },
            scales: {
                xAxes: [{
                    ticks: { beginAtZero: true, fontColor: '#ddd' },
                    gridLines: { display: true, color: "rgba(221, 221, 221, 0.08)" },
                }],
                yAxes: [{
                    ticks: { beginAtZero: true, fontColor: '#ddd' },
                    gridLines: { display: true, color: "rgba(221, 221, 221, 0.08)" },
                }]
            }
        }
    });

    // chart 2: 🔸 نمودار دایره‌ای فروش هفتگی 8 هفته اخیر
    var ctx2 = document.getElementById("chart2").getContext('2d');
    var myChart2 = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: weeklyLabels,
            datasets: [{
                backgroundColor: [
							"#ffffff",
							"rgba(255, 255, 255, 0.70)",
							"rgba(255, 255, 255, 0.50)",
							"rgba(255, 255, 255, 0.20)"
						],
                data: weeklyData,
                borderWidth: [0, 0, 0, 0]
            }]
        },
        options: {
            maintainAspectRatio: false,
            legend: {
                position: "bottom",
                display: false,
                labels: {
                    fontColor: '#ddd',
                    boxWidth: 15
                }
            },
            tooltips: { displayColors: false }
        }
    });

});
