document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/ativos')
        .then(response => response.json())
        .then(data => {
            let ativosSelect = document.getElementById('ativos');
            data.ativos.forEach(ativo => {
                let option = document.createElement('option');
                option.value = ativo;
                option.textContent = ativo;
                ativosSelect.appendChild(option);
            });
            updateChart(); // Atualiza o gráfico após carregar os ativos
        });

    fetch('/api/dollar')
        .then(response => response.json())
        .then(data => {
            document.getElementById('dollar-price').textContent = `USD to BRL: ${data.dollar_price}`;
        });
});

function updateChart() {
    let ativo = document.getElementById('ativos').value;
    fetch(`/api/data?ativo=${ativo}`)
        .then(response => response.json())
        .then(data => {
            let dates = data.map(entry => entry.date);
            let closes = data.map(entry => entry.close);

            let trace1 = {
                x: dates,
                y: closes,
                mode: 'lines',
                type: 'scatter'
            };

            let layout = {
                title: `Stock Prices for ${ativo}`,
                xaxis: { title: 'Date' },
                yaxis: { title: 'Close Price' }
            };

            Plotly.newPlot('chart', [trace1], layout);

            let tableBody = document.querySelector('#data-table tbody');
            tableBody.innerHTML = '';
            data.forEach(row => {
                let tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${new Date(row.date).toLocaleDateString()}</td>
                    <td>${row.open}</td>
                    <td>${row.high}</td>
                    <td>${row.low}</td>
                    <td>${row.close}</td>
                    <td>${row.ativo}</td>
                `;
                tableBody.appendChild(tr);
            });
        });
}

function analyzeData() {
    let prompt = document.getElementById('prompt').value;
    fetch('/api/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt: prompt })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('analysis-result').textContent = data.analysis;
    });
}
