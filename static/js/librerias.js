const tablas = document.querySelectorAll('table');

tablas.forEach(tabla =>{
    const opciones = {
        language: {
            url: 'https://cdn.datatables.net/plug-ins/2.3.2/i18n/es-ES.json'
        }
    };

    if (tabla.id === 'tablaRiesgos') {
        opciones.columnDefs = [
            { orderable: false, targets: [0, 6] }
        ];
    }

    $(tabla).DataTable(opciones);
});
