const tablas = document.querySelectorAll('table');

tablas.forEach(tabla =>{
    $(tabla).DataTable({
        language: {
            url: 'https://cdn.datatables.net/plug-ins/2.3.2/i18n/es-ES.json'
        }
    });})