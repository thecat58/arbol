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

document.addEventListener('DOMContentLoaded', function() {
    // Configuración inicial
    document.getElementById('current-question').textContent = "¡Bienvenido al Asistente de Selección Tecnológica!";
    document.getElementById('options-container').innerHTML = `
        <div class="welcome-message">
            Este asistente te ayudará a seleccionar la mejor tecnología para tu proyecto
            a través de una serie de preguntas organizadas en 5 fases.
        </div>
    `;
    
    document.getElementById('prevBtn').addEventListener('click', previousQuestion);
    document.getElementById('nextBtn').addEventListener('click', function() {
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
            headers: {
                'Content-Type': 'application/json'
            },
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