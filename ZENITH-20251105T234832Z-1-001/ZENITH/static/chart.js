let monthlyTrendChart = null;
let serviceDistributionChart = null;

const formatCOP = (value) => {
    return new Intl.NumberFormat('es-CO', { 
        style: 'currency', 
        currency: 'COP', 
        minimumFractionDigits: 0, 
        maximumFractionDigits: 0 
    }).format(value);
};


document.addEventListener('DOMContentLoaded', () => {

    (function handleAuthForms() {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const loginBtn = document.getElementById('login-btn');
        const registerBtn = document.getElementById('register-btn');
        const openRegisterLink = document.getElementById('open-register-link');
        const openLoginLink = document.getElementById('open-login-link');
        
        const adminSecretBtn = document.getElementById('admin-secret-button');

        const switchForm = (showLogin) => {
            if (loginForm && registerForm) {
                loginForm.style.display = showLogin ? 'block' : 'none';
                registerForm.style.display = showLogin ? 'none' : 'block';
            }
        };

        if (openRegisterLink) {
            openRegisterLink.addEventListener('click', (e) => { e.preventDefault(); switchForm(false); });
        }
        if (openLoginLink) {
            openLoginLink.addEventListener('click', (e) => { e.preventDefault(); switchForm(true); });
        }
        
        if (adminSecretBtn) {
            adminSecretBtn.addEventListener('click', (e) => {
                e.preventDefault();
                switchForm(true);
                document.getElementById('login-email').value = 'admin@zenith.com';
                document.getElementById('login-password').value = 'admin123';
                alert('Credenciales de administrador cargadas. Haz clic en "Ingresar".');
            });
        }
        
        const handleLogin = async (email, password) => {
            if (!email || !password) {
                alert('Por favor, complete todos los campos.'); return;
            }
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const result = await response.json();
                
                if (response.ok && result.success) {
                    alert(result.message);
                    window.location.href = result.redirect_url;
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                console.error('Error de conexión:', error);
                alert('Error de conexión con el servidor.');
            }
        };

        const handleRegister = async (username, email, password) => {
            const termsChecked = document.getElementById('register-terms').checked;
            
            if (!email || !password || !username) {
                alert('Por favor, complete todos los campos.'); return;
            }
            
            if (!termsChecked) {
                alert('Debe aceptar los Términos y Condiciones y la Política de Privacidad para registrarse.'); return;
            }
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, username })
                });
                const result = await response.json();
                if (response.ok && result.success) {
                    alert(result.message + ' Ahora puedes iniciar sesión.');
                    switchForm(true);
                } else {
                    alert('Error: ' + result.message);
                    switchForm(false);
                }
            } catch (error) {
                console.error('Error de conexión:', error);
                alert('Error de conexión con el servidor.');
            }
        };
        
        if (loginBtn) {
            loginBtn.addEventListener('click', () => {
                handleLogin(
                    document.getElementById('login-email').value,
                    document.getElementById('login-password').value
                );
            });
        }
        if (registerBtn) {
            registerBtn.addEventListener('click', () => {
                handleRegister(
                    document.getElementById('register-username').value,
                    document.getElementById('register-email').value,
                    document.getElementById('register-password').value
                );
            });
        }
    })();
    
    (function handleConsumoForm() {
        const guardarConsumoBtn = document.getElementById('guardarConsumoBtn');
        if (!guardarConsumoBtn) return; 
        
        const servicioSelect = document.getElementById('servicioSelect');
        const consumoUnitSpan = document.getElementById('consumoUnit');
        const consumoInput = document.getElementById('consumoInput');

        const unitMap = {
            'Electricidad': { unit: 'kWh', placeholder: 'Ej: 150' },
            'Agua': { unit: 'm³', placeholder: 'Ej: 25' },
            'Gas': { unit: 'm³', placeholder: 'Ej: 30' },
            'Internet': { unit: 'GB', placeholder: 'Ej: 100' }
        };

        const updateConsumoUnits = () => {
            const selectedService = servicioSelect.value;
            const info = unitMap[selectedService] || { unit: '(Uds.)', placeholder: 'Ej: 200.5' };
            
            if (consumoUnitSpan) {
                consumoUnitSpan.textContent = `(${info.unit})`;
            }
            if (consumoInput) {
                consumoInput.placeholder = info.placeholder;
            }
        };

        servicioSelect.addEventListener('change', updateConsumoUnits);
        updateConsumoUnits();
        
        guardarConsumoBtn.addEventListener('click', async () => {
            const servicio = document.getElementById('servicioSelect').value;
            const fecha = document.getElementById('fechaInput').value;
            let consumo = document.getElementById('consumoInput').value;
            let costo = document.getElementById('costoInput').value; 
            
            consumo = consumo.replace(',', '.');
            costo = costo.replace(',', '.');

            if (!servicio || !fecha || !consumo) {
                alert('Por favor, complete el Servicio, la Fecha y el Consumo.');
                return;
            }
            
            const consumoNum = parseFloat(consumo);
            const costoNum = costo ? parseFloat(costo) : null; 

            if (isNaN(consumoNum) || consumoNum <= 0) {
                 alert('❌ El Valor Consumo debe ser un número positivo válido.');
                 return;
            }

            if (costo && isNaN(costoNum)) {
                alert('❌ El Costo Total debe ser un número válido o dejarse vacío.');
                return;
            }

            const dataToSend = {
                servicio_nombre: servicio, 
                fecha: fecha,
                consumo: consumoNum,
                costo: costoNum
            };

            try {
                const response = await fetch('/api/guardar_consumo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataToSend)
                });
                const result = await response.json();
                if (response.ok && result.success) {
                    alert('✅ ' + result.message);
                    loadDashboardCharts();
                    document.getElementById('fechaInput').value = '';
                    document.getElementById('consumoInput').value = '';
                    document.getElementById('costoInput').value = '';
                } else {
                    alert('❌ Error al guardar: ' + result.message);
                }
            } catch (error) {
                console.error('Error de red o servidor:', error);
                alert('Ocurrió un error inesperado al conectar con el servidor.');
            }
        });
    })();
    
    const loadAnnualHistory = (annualData) => {
        const historyBody = document.getElementById('annualHistoryBody');
        if (!historyBody) return;

        historyBody.innerHTML = ''; 

        if (annualData.length === 0) {
            historyBody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 15px;">No hay registros de consumo anuales.</td></tr>';
            return;
        }
        
        annualData.forEach(history => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${history.anio}</td>
                <td>${history.Electricidad.toFixed(2)}</td>
                <td>${history.Agua.toFixed(2)}</td>
                <td>${history.Gas.toFixed(2)}</td>
                <td>${history.Internet.toFixed(2)}</td>
            `;
            historyBody.appendChild(row);
        });
    };
    
    const loadAlerts = async () => {
        const alertCardValue = document.getElementById('alertsValue'); 
        const alertSectionList = document.getElementById('alertas-list'); 
        const alertDashboardList = document.getElementById('dashboard-alertas-list'); 

        if (alertSectionList) alertSectionList.innerHTML = '<p>Cargando...</p>';
        if (alertDashboardList) alertDashboardList.innerHTML = '<p>Cargando...</p>';

        try {
            const cacheBuster = `?_=${new Date().getTime()}`;
            const response = await fetch(`/api/get_alertas${cacheBuster}`); 
            const data = await response.json();

            if (!data.success) {
                const errorMsg = `<p style="color: var(--danger-color);">Error: ${data.message}</p>`;
                if (alertSectionList) alertSectionList.innerHTML = errorMsg;
                if (alertDashboardList) alertDashboardList.innerHTML = errorMsg;
                if (alertCardValue) alertCardValue.textContent = 'Error';
                return;
            }

            const alertCount = data.alertas.length;
            
            if (alertCardValue) {
                alertCardValue.textContent = alertCount;
            }

            let listContent = '';
            if (alertCount === 0) {
                listContent = '<p>No tienes alertas ni recomendaciones por ahora. ¡Buen trabajo!</p>';
            } else {
                data.alertas.forEach(r => {
                    listContent += `
                        <div class="card recommendation-item" style="margin-bottom: 10px; border-left: 4px solid var(--danger-color);">
                            <p><strong>Servicio:</strong> ${r.servicio}</p>
                            <p>${r.texto}</p>
                            <small style="color: var(--link-color);">Fecha: ${r.fecha}</small>
                        </div>
                    `;
                });
            }
            
            if (alertSectionList) {
                alertSectionList.innerHTML = listContent;
            }
            if (alertDashboardList) {
                alertDashboardList.innerHTML = listContent;
            }

        } catch (error) {
            console.error('Error al cargar alertas:', error);
            const errorMsg = '<p style="color: var(--danger-color);">Error de conexión al cargar alertas.</p>';
            if (alertSectionList) alertSectionList.innerHTML = errorMsg;
            if (alertDashboardList) alertDashboardList.innerHTML = errorMsg;
            if (alertCardValue) alertCardValue.textContent = 'Error';
        }
    };

    const loadDashboardCharts = async () => {
        const ctxTrend = document.getElementById('monthlyTrendChart');
        
        if (!ctxTrend) return; 

        try {
            const cacheBuster = `?_=${new Date().getTime()}`;
            const response = await fetch(`/api/dashboard_data${cacheBuster}`);
            
            const data = await response.json();

            if (!data.success) {
                console.error('Error al cargar datos del dashboard:', data.message);
                return;
            }
            
            const chartColors = {
                'Electricidad': 'rgba(139, 233, 253, 0.7)',
                'Agua': 'rgba(80, 250, 123, 0.7)',
                'Gas': 'rgba(255, 85, 85, 0.7)',
                'Internet': 'rgba(189, 147, 249, 0.7)'
            };
            const borderColors = {
                'Electricidad': 'rgb(139, 233, 253)',
                'Agua': 'rgb(80, 250, 123)',
                'Gas': 'rgb(255, 85, 85)',
                'Internet': 'rgb(189, 147, 249)'
            };

            loadAnnualHistory(data.annual_history);

            const labelsMeses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
            const dataMeses = {}; 
            data.monthly_data.forEach(item => {
                if (!dataMeses[item.servicio]) {
                    dataMeses[item.servicio] = new Array(12).fill(0);
                }
                dataMeses[item.servicio][item.mes - 1] = item.total;
            });
            const datasetsTrend = Object.keys(dataMeses).map(servicio => {
                return {
                    label: servicio,
                    data: dataMeses[servicio],
                    backgroundColor: chartColors[servicio] || 'rgba(255, 255, 255, 0.5)',
                    borderColor: borderColors[servicio] || 'rgb(255, 255, 255)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                };
            });
            
            document.getElementById('totalConsValue').textContent = formatCOP(data.total_cost_current_month);
            
            const savingsEl = document.getElementById('savingsValue');
            const ahorroVal = data.ahorro_estimado;
            savingsEl.textContent = formatCOP(ahorroVal);
            if (ahorroVal < 0) {
                savingsEl.style.color = 'var(--danger-color)';
            } else {
                savingsEl.style.color = 'var(--primary-color)';
            }

            if (monthlyTrendChart) monthlyTrendChart.destroy();

            monthlyTrendChart = new Chart(ctxTrend, {
                type: 'line',
                data: { labels: labelsMeses, datasets: datasetsTrend },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true, title: { display: true, text: 'Consumo (Uds.)' } } }
                }
            });
            
            loadAlerts();

        } catch (error) {
            console.error('Error al cargar datos del dashboard:', error);
        }
    };
    
    const loadFacturas = async () => {
        const facturasBody = document.getElementById('facturasHistoryBody');
        if (!facturasBody) return;
        
        facturasBody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 10px;">Cargando...</td></tr>';
        
        try {
            const cacheBuster = `?_=${new Date().getTime()}`;
            const response = await fetch(`/api/get_facturas${cacheBuster}`);
            const data = await response.json();
            
            if (data.success) {
                facturasBody.innerHTML = '';
                if (data.facturas.length === 0) {
                    facturasBody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 10px;">No has subido ninguna factura.</td></tr>';
                } else {
                    data.facturas.forEach(f => {
                        const row = document.createElement('tr');
                        const archivoLink = f.archivo_url 
                            ? `<a href="${f.archivo_url}" target="_blank" style="color: var(--accent-color);">Ver Archivo</a>` 
                            : 'No adjunto';
                            
                        row.innerHTML = `
                            <td>${f.periodo}</td>
                            <td>${formatCOP(f.monto_total)}</td>
                            <td>${archivoLink}</td>
                        `;
                        facturasBody.appendChild(row);
                    });
                }
            } else {
                facturasBody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--danger-color);">Error: ${data.message}</td></tr>`;
            }
        } catch (error) {
            console.error('Error al cargar facturas:', error);
            facturasBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--danger-color);">Error de conexión.</td></tr>';
        }
    };
    
    (function handleFacturaUpload() {
        const form = document.getElementById('facturaUploadForm');
        const btn = document.getElementById('guardarFacturaBtn');
        if (!form || !btn) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            btn.textContent = 'Subiendo...';
            btn.disabled = true;
            
            const periodo = document.getElementById('facturaPeriodoInput').value;
            const monto = document.getElementById('facturaMontoInput').value;
            const fileInput = document.getElementById('facturaFileInput');
            
            if (!periodo || !monto || fileInput.files.length === 0) {
                alert('Por favor, complete todos los campos y seleccione un archivo.');
                btn.textContent = 'Subir Factura';
                btn.disabled = false;
                return;
            }
            
            const formData = new FormData();
            formData.append('periodo', periodo);
            formData.append('monto', monto);
            formData.append('facturaFile', fileInput.files[0]);
            
            try {
                const response = await fetch('/api/subir_factura', {
                    method: 'POST',
                    body: formData 
                });
                const result = await response.json();
                
                if (response.ok && result.success) {
                    alert('✅ ' + result.message);
                    form.reset();
                    loadFacturas(); 
                } else {
                    alert('❌ Error al subir: ' + result.message);
                }
            } catch (error) {
                console.error('Error de red:', error);
                alert('Error de conexión al subir el archivo.');
            } finally {
                btn.textContent = 'Subir Factura';
                btn.disabled = false;
            }
        });
    })();

    (function handleEvaluacionSubmit() {
        const form = document.getElementById('evaluacionForm');
        const btn = document.getElementById('guardarEvaluacionBtn');
        if (!form || !btn) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            btn.textContent = 'Enviando...';
            btn.disabled = true;
            
            const calificacion = document.getElementById('evaluacionCalificacion').value;
            const comentario = document.getElementById('evaluacionComentario').value;

            if (!calificacion) {
                alert('Por favor, selecciona una calificación.');
                btn.textContent = 'Enviar Evaluación';
                btn.disabled = false;
                return;
            }

            try {
                const response = await fetch('/api/guardar_evaluacion', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ calificacion, comentario })
                });
                const result = await response.json();
                
                if (response.ok && result.success) {
                    alert('✅ ' + result.message);
                    form.reset();
                } else {
                    alert('❌ Error: ' + result.message);
                }
            } catch (error) {
                console.error('Error de red:', error);
                alert('Error de conexión.');
            } finally {
                btn.textContent = 'Enviar Evaluación';
                btn.disabled = false;
            }
        });
    })();
    
    (function handleProfileUpdate() {
        const btn = document.getElementById('updateProfileButton');
        if (!btn) return;

        btn.addEventListener('click', async () => {
            const username = document.getElementById('profileUsername').value;
            const email = document.getElementById('profileEmail').value;
            const currentPassword = document.getElementById('profileCurrentPassword').value;
            const newPassword = document.getElementById('profileNewPassword').value;

            if (!username || !email) {
                alert('El nombre de usuario y el email no pueden estar vacíos.');
                return;
            }

            if (newPassword && !currentPassword) {
                alert('Debes ingresar tu contraseña actual para establecer una nueva.');
                return;
            }

            const dataToSend = {
                username,
                email,
                current_password: currentPassword || null,
                password: newPassword || null
            };

            try {
                btn.textContent = 'Guardando...';
                btn.disabled = true;

                const response = await fetch('/api/actualizar_perfil', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataToSend)
                });
                const result = await response.json();

                if (response.ok && result.success) {
                    alert('✅ ' + result.message);
                    
                    document.getElementById('welcome-message').textContent = `Bienvenido, ${result.new_username}!`;
                    document.getElementById('modal-welcome-message').textContent = `Hola, ${result.new_username}!`;
                    document.getElementById('profileCurrentPassword').value = '';
                    document.getElementById('profileNewPassword').value = '';
                } else {
                    alert('❌ Error: ' + result.message);
                }

            } catch (error) {
                console.error('Error de red:', error);
                alert('Error de conexión al actualizar el perfil.');
            } finally {
                btn.textContent = 'Guardar Cambios';
                btn.disabled = false;
            }
        });
    })();
    
    const loadAvatar = () => {
        if (typeof CURRENT_USER_ID === 'undefined' || !CURRENT_USER_ID) return;
        
        const AVATAR_KEY = `user-avatar-${CURRENT_USER_ID}`;
        const avatarData = localStorage.getItem(AVATAR_KEY);
        const headerAvatarContainer = document.getElementById('header-avatar-container');
        const modalAvatarPreview = document.getElementById('avatar-preview-container');

        let avatarHtml = '<i class="fas fa-user-circle user-icon"></i>';
        
        if (avatarData) {
            avatarHtml = `<img src="${avatarData}" class="user-icon" alt="Avatar">`;
        }

        if (headerAvatarContainer) {
            headerAvatarContainer.innerHTML = avatarHtml;
        }
        if (modalAvatarPreview) {
            if (avatarData) {
                modalAvatarPreview.innerHTML = `<img src="${avatarData}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover;" alt="Avatar">`;
            } else {
                modalAvatarPreview.innerHTML = '<i class="fas fa-user-circle user-icon" style="font-size: 100px; color: var(--accent-color);"></i>';
            }
        }
    };

    (function handleProfileModal() {
        const modal = document.getElementById('profileModal');
        const openBtn = document.getElementById('userProfileButton');
        const closeBtn = document.getElementById('closeProfileModal');
        const saveBtn = document.getElementById('saveAvatarButton');
        const fileInput = document.getElementById('avatarUpload');
        const previewContainer = document.getElementById('avatar-preview-container');

        if (!modal || !openBtn || !closeBtn || !saveBtn || !fileInput || typeof CURRENT_USER_ID === 'undefined' || !CURRENT_USER_ID) {
            return;
        }
        
        const AVATAR_KEY = `user-avatar-${CURRENT_USER_ID}`;
        let newAvatarData = null;

        openBtn.addEventListener('click', () => {
            modal.style.display = 'flex';
            loadAvatar(); 
            newAvatarData = null; 
            fileInput.value = ''; 
        });

        const closeModal = () => {
            modal.style.display = 'none';
        };
        closeBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) { 
                closeModal();
            }
        });

        fileInput.addEventListener('change', () => {
            const file = fileInput.files[0];
            if (file && (file.type === 'image/png' || file.type === 'image/jpeg')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    newAvatarData = e.target.result;
                    previewContainer.innerHTML = `<img src="${newAvatarData}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover;" alt="Preview">`;
                };
                reader.readAsDataURL(file);
            } else {
                alert('Por favor, selecciona un archivo PNG o JPG.');
                newAvatarData = null;
            }
        });

        saveBtn.addEventListener('click', () => {
            if (newAvatarData) {
                localStorage.setItem(AVATAR_KEY, newAvatarData);
                loadAvatar(); 
                alert('¡Foto de perfil actualizada!');
                closeModal();
            } else {
                alert('No has seleccionado una nueva foto.');
            }
        });

    })();

    (function handleSPANavigation() {
        const sidebarLinks = document.querySelectorAll('.menu ul li a');
        const contentSections = document.querySelectorAll('.main-content .view');
        const menuItems = document.querySelectorAll('.menu ul li');

        const sectionMap = {
            'dashboardLink': '.main-dashboard-content',
            'miConsumoLink': '#sectionMiConsumo',
            'historialLink': '#sectionHistorial', 
            'facturasLink': '#sectionFacturas', 
            'alertasLink': '#sectionAlertas',
            'configuracionLink': '#sectionConfiguracion',
            'evaluacionLink': '#sectionEvaluacion', 
            'ayudaLink': '#sectionAyuda'
        };

        const showSection = (targetSelector) => {
            contentSections.forEach(section => section.classList.remove('active'));
            menuItems.forEach(item => item.classList.remove('active'));

            const targetSection = document.querySelector(targetSelector);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        };

        sidebarLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                if (link.getAttribute('href') === '#') {
                    e.preventDefault();
                }
                const linkId = link.id;
                if (linkId === 'logoutLink') return;

                const targetSectionSelector = sectionMap[linkId];
                
                if (targetSectionSelector) {
                    showSection(targetSectionSelector);
                    if (link.parentElement) {
                        link.parentElement.classList.add('active');
                    }
                    
                    if (linkId === 'dashboardLink' || linkId === 'historialLink') {
                        loadDashboardCharts();
                    } else if (linkId === 'alertasLink') {
                        loadAlerts(); 
                    } else if (linkId === 'facturasLink') {
                        loadFacturas(); 
                    }
                }
            });
        });
    })();
    
    (function handleLanguageSwitch() {
        const translations = {
            "es": {
                "lang-es": "Español",
                "lang-en": "Inglés",
                "lang-pt": "Portugués",
                "theme-dark": "Oscuro",
                "theme-light": "Claro",
                "welcomeMsg": "Bienvenido,", 
                "totalConsTitle": "Costo Total Mes",
                "savingsTitle": "Ahorro Estimado (vs Mes Pasado)",
                "alertsTitle": "Alertas Activas",
                "annualChartTitle": "Consumo Mensual por Servicio (Año Actual)",
                "monthlyChartTitle": "Distribución Total de Consumo",
                "miConsumoTitle": "Mi Consumo",
                "newRegTitle": "Nuevo Registro de Gasto",
                "servicioLabel": "Servicio:",
                "fechaLabel": "Fecha del Consumo:",
                "consumoLabel": "Valor Consumo",
                "costoLabel": "Costo total (COP) (Opcional):",
                "guardarBtn": "Guardar Gasto",
                "historialTitle": "Historial Anual de Consumo",
                "facturasTitle": "Mis Facturas",
                "newFacturaTitle": "Subir Nueva Factura",
                "alertasSectionTitle": "Alertas y Notificaciones",
                "recoTitle": "Mis Alertas y Recomendaciones",
                "configTitle": "Configuración",
                "evaluacionTitle": "Evaluar Aplicación",
                "evalFormTitle": "¿Cómo ha sido tu experiencia? (CUD 010)",
                "helpTitle": "Ayuda",
                "dashboardLink": "Dashboard",
                "miConsumoLink": "Mi Consumo",
                "historialLink": "Historial Anual",
                "facturasLink": "Mis Facturas",
                "alertasLink": "Alertas y Notificaciones",
                "configuracionLink": "Configuración",
                "evaluacionLink": "Evaluar Aplicación",
                "ayudaLink": "Ayuda",
                "logoutLink": "Cerrar Sesión"
            },
            "en": {
                "lang-es": "Spanish",
                "lang-en": "English",
                "lang-pt": "Portuguese",
                "theme-dark": "Dark",
                "theme-light": "Light",
                "welcomeMsg": "Welcome,",
                "totalConsTitle": "Total Cost This Month",
                "savingsTitle": "Estimated Savings (vs Last Month)",
                "alertsTitle": "Active Alerts",
                "annualChartTitle": "Monthly Consumption by Service (Current Year)",
                "monthlyChartTitle": "Total Consumption Distribution",
                "miConsumoTitle": "My Consumption",
                "newRegTitle": "New Expense Entry",
                "servicioLabel": "Service:",
                "fechaLabel": "Consumption Date:",
                "consumoLabel": "Consumption Value",
                "costoLabel": "Total Cost (COP) (Optional):",
                "guardarBtn": "Save Expense",
                "historialTitle": "Annual Consumption History",
                "facturasTitle": "My Invoices",
                "newFacturaTitle": "Upload New Invoice",
                "alertasSectionTitle": "Alerts and Notifications",
                "recoTitle": "My Alerts and Recommendations",
                "configTitle": "Settings",
                "evaluacionTitle": "Evaluate Application",
                "evalFormTitle": "How has your experience been? (CUD 010)",
                "helpTitle": "Help",
                "dashboardLink": "Dashboard",
                "miConsumoLink": "My Consumption",
                "historialLink": "Annual History",
                "facturasLink": "My Invoices",
                "alertasLink": "Alerts & Notifications",
                "configuracionLink": "Settings",
                "evaluacionLink": "Evaluate App",
                "ayudaLink": "Help",
                "logoutLink": "Log Out"
            },
            "pt": {
                "lang-es": "Espanhol",
                "lang-en": "Inglês",
                "lang-pt": "Português",
                "theme-dark": "Escuro",
                "theme-light": "Claro",
                "welcomeMsg": "Bem-vindo,",
                "totalConsTitle": "Custo Total Mês",
                "savingsTitle": "Economia Estimada (vs Mês Passado)",
                "alertsTitle": "Alertas Ativos",
                "annualChartTitle": "Consumo Mensal por Serviço (Ano Atual)",
                "monthlyChartTitle": "Distribuição Total de Consumo",
                "miConsumoTitle": "Meu Consumo",
                "newRegTitle": "Novo Registro de Despesa",
                "servicioLabel": "Serviço:",
                "fechaLabel": "Data do Consumo:",
                "consumoLabel": "Valor de Consumo",
                "costoLabel": "Custo Total (COP) (Opcional):",
                "guardarBtn": "Salvar Despesa",
                "historialTitle": "Histórico Anual de Consumo",
                "facturasTitle": "Minhas Faturas",
                "newFacturaTitle": "Carregar Nova Fatura",
                "alertasSectionTitle": "Alertas e Notificações",
                "recoTitle": "Meus Alertas e Recomendações",
                "configTitle": "Configurações",
                "evaluacionTitle": "Avaliar Aplicação",
                "evalFormTitle": "Como tem sido sua experiência? (CUD 010)",
                "helpTitle": "Ajuda",
                "dashboardLink": "Dashboard",
                "miConsumoLink": "Meu Consumo",
                "historialLink": "Histórico Anual",
                "facturasLink": "Minhas Faturas",
                "alertasLink": "Alertas e Notificações",
                "configuracionLink": "Configurações",
                "evaluacionLink": "Avaliar App",
                "ayudaLink": "Ajuda",
                "logoutLink": "Sair"
            }
        };

        const langSelectors = document.querySelectorAll('[id^="language-select-"]');
        
        const translatePage = (lang) => {
            if (!translations[lang]) {
                console.warn(`Language ${lang} not found in translations.`);
                return;
            }
            
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                const translation = translations[lang][key];
                
                if (translation) {
                    if (el.tagName === 'A' && el.querySelector('i')) {
                        for (let node of el.childNodes) {
                            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0) {
                                node.textContent = ' ' + translation; 
                                break;
                            }
                        }
                    } else {
                        el.textContent = translation;
                    }
                } else {
                    console.warn(`Translation key "${key}" not found for lang "${lang}".`);
                }
            });
            
            langSelectors.forEach(s => s.value = lang);
            localStorage.setItem('zenith-lang', lang);
        };

        langSelectors.forEach(select => {
            select.addEventListener('change', (e) => {
                translatePage(e.target.value);
            });
        });

        const currentLang = localStorage.getItem('zenith-lang') || 'es';
        translatePage(currentLang);

    })(); 
    
    (function handleThemeSwitch() {
        const html = document.getElementById('html');
        const themeSelects = document.querySelectorAll('[id^="theme-select-"]');
        
        const currentTheme = localStorage.getItem('zenith-theme') || 'dark';
        if (html) html.classList.add(currentTheme + '-theme');

        themeSelects.forEach(select => {
            if (select) {
                select.value = currentTheme;
                select.addEventListener('change', (e) => {
                    const newTheme = e.target.value;
                    if (html) {
                        html.classList.remove('dark-theme', 'light-theme');
                        html.classList.add(newTheme + '-theme');
                    }
                    localStorage.setItem('zenith-theme', newTheme);
                    themeSelects.forEach(s => s.value = newTheme);
                });
            }
        });
    })();

    loadAvatar();

    if (document.getElementById('monthlyTrendChart')) {
        loadDashboardCharts();
    }
});