let estado_sider = localStorage.getItem('estado_sider') ?? 1;
var sidebar = document.getElementById('sidebar');
var mainContent = document.getElementById('mainContent');
var menu = document.getElementById('btnToggleSidebar');
const accion_estado = () => {
    if (estado_sider == 1){
        sidebar.classList.remove('oculto');
        mainContent.classList.remove('expanded')
    }else{
        sidebar.classList.add('oculto');
        mainContent.classList.add('expanded')
    }
}
accion_estado();

//procedimiento

const accion_menu = () => {
    estado_sider = estado_sider == 1 ? 0 : 1 ;
    localStorage.setItem('estado_sider', estado_sider);
    accion_estado();

}

menu.addEventListener('click', function(){
    accion_menu();
})