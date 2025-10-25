let currentPhase = 1;
let currentQuestion = 0;
let questions = [];
let answers = {};

const phaseDescriptions = {
    1: "Identificación del Proyecto",
    2: "Requerimientos Técnicos",
    3: "Gestión de Datos",
    4: "Contexto de Desarrollo",
    5: "Consideraciones Específicas"
};

document.addEventListener('DOMContentLoaded', function () {
    // Configuración inicial
    document.getElementById('current-question').textContent = "¡Bienvenido al Asistente de Selección Tecnológica!";
    document.getElementById('options-container').innerHTML = `
        <div class="welcome-message">
            Este asistente te ayudará a seleccionar la mejor tecnología para tu proyecto
            a través de una serie de preguntas organizadas en 5 fases.
        </div>
    `;

    document.getElementById('prevBtn').addEventListener('click', previousQuestion);
    document.getElementById('nextBtn').addEventListener('click', function () {
        if (this.textContent === 'Comenzar') {
            loadPhase(currentPhase);
            this.textContent = 'Siguiente';
        } else {
            nextQuestion();
        }
    });
});

async function loadPhase(phase) {
    try {
        const response = await fetch(`/questions/${phase}`);
        questions = await response.json();
        console.log('Loaded questions for phase', phase, questions);

        // reset current question index for the phase
        currentQuestion = 0;
        if (questions.length > 0) {
            // update phase title
            const phaseTitle = document.getElementById('current-phase-title');
            if (phaseTitle) phaseTitle.textContent = phaseDescriptions[phase] || `Fase ${phase}`;

            showQuestion(currentQuestion);
            updateProgressBar();
        } else {
            // no questions in this phase
            document.getElementById('current-question').textContent = 'No hay preguntas en esta fase.';
            document.getElementById('options-container').innerHTML = '';
        }
    } catch (error) {
        console.error('Error loading questions:', error);
    }
}

function showQuestion(index) {
    if (!questions[index]) return;

    const question = questions[index];
    document.getElementById('current-question').textContent = question.text;
    // show optional description if provided
    const qdesc = document.getElementById('question-description');
    if (qdesc) qdesc.textContent = question.metadata?.description || '';

    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '';

    question.options.forEach(option => {
        const optionCard = document.createElement('div');
        optionCard.className = 'option-card';
        optionCard.textContent = option.text;
        optionCard.dataset.optionId = option.id;

        if (answers[question.id] === option.id) {
            optionCard.classList.add('selected');
        }

        optionCard.addEventListener('click', () => selectOption(question.id, option.id));
        optionsContainer.appendChild(optionCard);
    });

    updateNavigationButtons();
}

function selectOption(questionId, optionId) {
    answers[questionId] = optionId;

    const options = document.querySelectorAll('.option-card');
    options.forEach(opt => opt.classList.remove('selected'));

    const selectedOption = document.querySelector(`[data-option-id="${optionId}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
    }

    document.getElementById('nextBtn').disabled = false;
    // small UX: avanzar automáticamente a la siguiente pregunta después de seleccionar
    setTimeout(() => {
        // only advance if button still shows 'Siguiente'
        const nextBtn = document.getElementById('nextBtn');
        if (nextBtn && nextBtn.textContent.trim() === 'Siguiente') {
            nextQuestion();
        }
    }, 350);
}

function updateProgressBar() {
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach((step, index) => {
        step.classList.remove('active', 'completed');
        if (index + 1 === currentPhase) {
            step.classList.add('active');
        } else if (index + 1 < currentPhase) {
            step.classList.add('completed');
        }
    });
}

function previousQuestion() {
    if (currentQuestion > 0) {
        currentQuestion--;
        showQuestion(currentQuestion);
    } else if (currentPhase > 1) {
        currentPhase--;
        loadPhase(currentPhase);
    }
}

function nextQuestion() {
    if (currentQuestion < questions.length - 1) {
        currentQuestion++;
        showQuestion(currentQuestion);
    } else if (currentPhase < 5) {
        currentPhase++;
        currentQuestion = 0;
        loadPhase(currentPhase);
    } else {
        showResults();
    }
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    // Si estamos en la pantalla de bienvenida
    if (nextBtn.textContent === 'Comenzar') {
        prevBtn.disabled = true;
        nextBtn.disabled = false;
        return;
    }

    prevBtn.disabled = currentPhase === 1 && currentQuestion === 0;
    nextBtn.textContent = (currentPhase === 5 && currentQuestion === questions.length - 1) ? 'Finalizar' : 'Siguiente';
    nextBtn.disabled = !answers[questions[currentQuestion]?.id];
}

async function showResults() {
    document.getElementById('question-container').classList.add('hidden');
    document.getElementById('navigation').classList.add('hidden');
    document.getElementById('results').classList.remove('hidden');

    try {
        // Convertir respuestas al formato esperado por la API
        const answersArray = Object.entries(answers).map(([questionId, answerId]) => ({
            questionId,
            answerId,
            phase: questions.find(q => q.id === questionId)?.phase || 1
        }));

        // Obtener recomendaciones del servidor
        const response = await fetch('/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(answersArray)
        });
        const recommendations = await response.json();

        // Mostrar recomendaciones por categoría
        Object.entries(recommendations).forEach(([category, items]) => {
            const container = document.querySelector(`#${category}-recommendations .recommendation-content`);
            if (container && items.length > 0) {
                container.innerHTML = `
                    <ul>
                        ${items.map(item => `<li>${item}</li>`).join('')}
                    </ul>
                `;
            }
        });

        // Guardar la sesión
        const sessionId = Date.now().toString();
        await fetch('/save-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: sessionId,
                answers: answersArray,
                timestamp: new Date().toISOString()
            })
        });

        // Configurar botones de exportación
        setupExportButtons(recommendations);
    } catch (error) {
        console.error('Error al generar recomendaciones:', error);
        document.getElementById('results').innerHTML = `
            <div class="error-message">
                Lo sentimos, hubo un error al generar las recomendaciones.
                Por favor, intenta nuevamente.
            </div>
        `;
    }
}

function setupExportButtons(recommendations) {
    document.getElementById('exportPDF').addEventListener('click', () => exportPDF(recommendations));
    document.getElementById('exportJSON').addEventListener('click', () => exportJSON(recommendations));
    document.getElementById('startNew').addEventListener('click', () => window.location.reload());
}

function exportPDF(recommendations) {
    // Aquí se implementaría la exportación a PDF
    console.log('Exportando a PDF:', recommendations);
    alert('La exportación a PDF estará disponible próximamente');
}

function exportJSON(recommendations) {
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/json;charset=utf-8,' +
        encodeURIComponent(JSON.stringify(recommendations, null, 2)));
    element.setAttribute('download', `recomendaciones_${Date.now()}.json`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

// Script ligero para obtener preguntas y controlar la navegación del cuestionario
(async function () {
    async function fetchQuestions() {
        const res = await fetch('/api/questions');
        if (!res.ok) throw new Error('No se pudo cargar /api/questions');
        return res.json();
    }

    function flattenQuestions(phases) {
        const list = [];
        for (const phase of phases) {
            const phaseTitle = phase.text || '';
            const children = phase.children || [];
            for (const ch of children) {
                if (ch.type === 'question' || ch.node_type === 'question') {
                    const options = (ch.children || [])
                        .filter(c => c.type === 'option' || c.node_type === 'option')
                        .map(o => ({
                            id: o.id,
                            text: o.text,
                            label: o.original_text || o.text || o.id
                        }));
                    list.push({
                        id: ch.id,
                        text: ch.text,
                        phase: ch.phase ?? null,
                        phaseTitle,
                        options
                    });
                }

            }
        }
        return list;
    }

    function createUI() {
        document.body.innerHTML = '';
        const root = document.createElement('div');
        root.id = 'qa-app';
        root.className = 'qa-root';

        const header = document.createElement('header');
        header.className = 'qa-header';
        header.innerHTML = '<h1>Asistente — Cuestionario</h1><p>Responde para obtener recomendaciones claras y prácticas.</p>';
        root.appendChild(header);

        const timeline = document.createElement('div');
        timeline.id = 'timeline';
        timeline.className = 'timeline';
        root.appendChild(timeline);

        const card = document.createElement('div');
        card.className = 'qa-card';

        const phaseEl = document.createElement('div');
        phaseEl.id = 'phaseTitle';
        phaseEl.className = 'phase-title';
        card.appendChild(phaseEl);

        const qEl = document.createElement('div');
        qEl.id = 'questionText';
        qEl.className = 'question-text';
        card.appendChild(qEl);

        const opts = document.createElement('div');
        opts.id = 'options';
        opts.className = 'options';
        card.appendChild(opts);

        const nav = document.createElement('div');
        nav.className = 'nav';
        const prevBtn = document.createElement('button');
        prevBtn.id = 'prevBtn';
        prevBtn.className = 'btn';
        prevBtn.textContent = 'Anterior';
        const nextBtn = document.createElement('button');
        nextBtn.id = 'nextBtn';
        nextBtn.className = 'btn primary';
        nextBtn.textContent = 'Siguiente';
        const submitBtn = document.createElement('button');
        submitBtn.id = 'submitBtn';
        submitBtn.className = 'btn success';
        submitBtn.textContent = 'Finalizar';
        submitBtn.style.display = 'none';

        nav.appendChild(prevBtn);
        nav.appendChild(nextBtn);
        nav.appendChild(submitBtn);
        card.appendChild(nav);

        const result = document.createElement('div');
        result.id = 'result';
        result.className = 'result';
        card.appendChild(result);

        root.appendChild(card);
        document.body.appendChild(root);

        return { timeline, phaseEl, qEl, opts, prevBtn, nextBtn, submitBtn, result };
    }

    function buildTimeline(container, total) {
        container.innerHTML = '';
        const bar = document.createElement('div');
        bar.className = 'timeline-bar';
        const fill = document.createElement('div');
        fill.className = 'timeline-fill';
        fill.style.width = '0%';
        bar.appendChild(fill);
        container.appendChild(bar);

        const steps = document.createElement('div');
        steps.className = 'timeline-steps';
        for (let i = 0; i < total; i++) {
            const s = document.createElement('div');
            s.className = 'timeline-step';
            s.dataset.index = i;
            s.textContent = (i + 1);
            steps.appendChild(s);
        }
        container.appendChild(steps);
        return { fill, steps };
    }

    function updateTimeline(tl, answeredCount, total) {
        const percent = Math.round((answeredCount / total) * 100);
        tl.fill.style.width = percent + '%';
        Array.from(tl.steps.children).forEach((s, idx) => {
            s.classList.toggle('done', idx < answeredCount);
            s.classList.toggle('current', idx === answeredCount);
        });
    }

    function renderQuestion(q, ui, selectedId) {
        ui.phaseEl.textContent = q.phaseTitle ? `${q.phaseTitle} (Fase ${q.phase ?? ''})` : '';
        ui.qEl.textContent = q.text;
        ui.opts.innerHTML = '';
        if (!q.options || q.options.length === 0) {
            const p = document.createElement('div');
            p.textContent = 'Sin opciones.';
            ui.opts.appendChild(p);
            return;
        }
        q.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'opt-btn';
            btn.textContent = opt.text || opt.label || opt.id;
            if (selectedId === opt.id) btn.classList.add('selected');
            btn.onclick = () => {
                // marcar visual y guardar
                Array.from(ui.opts.querySelectorAll('.opt-btn')).forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                selections[q.id] = { questionId: q.id, answerId: opt.id, phase: q.phase };
                // actualizar timeline
                updateTimeline(timelineState, Object.keys(selections).length, questions.length);
            };
            ui.opts.appendChild(btn);
        });
    }

    function renderRecommendations(data) {
        ui.result.innerHTML = '';
        const title = document.createElement('h2');
        title.textContent = 'Recomendaciones';
        ui.result.appendChild(title);

        const grid = document.createElement('div');
        grid.className = 'rec-grid';

        const order = ['frontend', 'backend', 'database', 'architecture', 'methodology', 'security'];
        const labels = {
            frontend: 'Frontend',
            backend: 'Backend',
            database: 'Base de datos',
            architecture: 'Arquitectura',
            methodology: 'Metodología',
            security: 'Seguridad'
        };

        order.forEach(cat => {
            const items = data[cat] || [];
            const card = document.createElement('div');
            card.className = 'rec-card';
            const h = document.createElement('h3');
            h.textContent = labels[cat];
            card.appendChild(h);
            if (items.length === 0) {
                const p = document.createElement('p');
                p.className = 'muted';
                p.textContent = 'No hay recomendaciones específicas.';
                card.appendChild(p);
            } else {
                const ul = document.createElement('ul');
                items.forEach(it => {
                    const li = document.createElement('li');
                    li.textContent = it;
                    ul.appendChild(li);
                });
                card.appendChild(ul);
            }
            grid.appendChild(card);
        });

        // Summary box con acciones a seguir
        const summary = document.createElement('div');
        summary.className = 'rec-summary';
        summary.innerHTML = `<h3>Pasos recomendados</h3>
      <ol>
        <li>Prioriza la fase mínima viable (MVP) y elige stack recomendado para frontend y backend.</li>
        <li>Configura una base de datos gestionada (Postgres) y backups.</li>
        <li>Implementa CI/CD y monitorización básica.</li>
        <li>Planifica seguridad básica: HTTPS, autenticación y backups.</li>
      </ol>`;
        ui.result.appendChild(grid);
        ui.result.appendChild(summary);
    }

    // main
    let questions = [];
    let index = 0;
    const selections = {};
    const ui = createUI();
    let timelineState = null;

    ui.prevBtn.onclick = () => {
        if (index > 0) {
            index--;
            ui.nextBtn.style.display = '';
            ui.submitBtn.style.display = 'none';
            ui.prevBtn.disabled = index === 0;
            renderQuestion(questions[index], ui, selections[questions[index].id]?.answerId);
        }
    };
    ui.nextBtn.onclick = () => {
        const curQ = questions[index];
        if (!selections[curQ.id]) {
            alert('Selecciona una opción para continuar.');
            return;
        }
        if (index < questions.length - 1) {
            index++;
            ui.prevBtn.disabled = false;
            if (index === questions.length - 1) {
                ui.nextBtn.style.display = 'none';
                ui.submitBtn.style.display = '';
            }
            renderQuestion(questions[index], ui, selections[questions[index].id]?.answerId);
        }
    };
    ui.submitBtn.onclick = async () => {
        const arr = Object.values(selections);
        if (arr.length < questions.length) {
            if (!confirm('No respondiste todas las preguntas. ¿Enviar de todas formas?')) return;
        }
        ui.submitBtn.disabled = true;
        ui.submitBtn.textContent = 'Enviando...';
        try {
            const res = await fetch('/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(arr)
            });
            if (!res.ok) throw new Error('Error al evaluar respuestas');
            const data = await res.json();
            renderRecommendations(data);
            // marcar progress full
            updateTimeline(timelineState, questions.length, questions.length);
        } catch (e) {
            ui.result.textContent = 'Error: ' + e.message;
        } finally {
            ui.submitBtn.disabled = false;
            ui.submitBtn.textContent = 'Finalizar';
        }
    };

    try {
        const phases = await fetchQuestions();
        questions = flattenQuestions(phases);
        if (questions.length === 0) {
            document.body.innerHTML = '<div class="empty">No se encontraron preguntas en el flujo.</div>';
            return;
        }
        timelineState = buildTimeline(ui.timeline, questions.length);
        renderQuestion(questions[index], ui, selections[questions[index].id]?.answerId);
        updateTimeline(timelineState, 0, questions.length);
        ui.prevBtn.disabled = true;
        if (questions.length === 1) {
            ui.nextBtn.style.display = 'none';
            ui.submitBtn.style.display = '';
        }
    } catch (err) {
        document.body.innerHTML = '<div class="error">Error cargando preguntas: ' + err.message + '</div>';
    }
})();