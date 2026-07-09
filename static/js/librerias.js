const tablas = document.querySelectorAll('table[id^="tabla"]');

const idiomaDataTables = {
    decimal: '',
    emptyTable: 'No hay datos disponibles en la tabla',
    info: 'Mostrando _START_ a _END_ de _TOTAL_ registros',
    infoEmpty: 'Mostrando 0 a 0 de 0 registros',
    infoFiltered: '(filtrado de _MAX_ registros totales)',
    lengthMenu: 'Mostrar _MENU_ registros',
    loadingRecords: 'Cargando...',
    processing: 'Procesando...',
    search: 'Buscar:',
    zeroRecords: 'No se encontraron resultados',
    paginate: {
        first: 'Primero',
        last: 'Último',
        next: 'Siguiente',
        previous: 'Anterior'
    },
    aria: {
        sortAscending: ': activar para ordenar ascendente',
        sortDescending: ': activar para ordenar descendente'
    }
};

tablas.forEach(tabla => {
    if ($.fn.DataTable.isDataTable(tabla)) {
        return;
    }

    const opciones = {
        language: idiomaDataTables
    };

    if (tabla.id === 'tablaRiesgos') {
        opciones.columnDefs = [
            { orderable: false, targets: [5] }
        ];
    }

    $(tabla).DataTable(opciones);
});
