import customtkinter as ctk
import firebase_admin
from firebase_admin import credentials, db
import threading
import os

# Configuración visual moderna de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AppEnvios(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana principal
        self.title("📦 Envíos 53 - Panel de Logística de TeleUPM")
        self.geometry("950x700")
        self.minsize(800, 500)

        # Cabecera
        self.label_titulo = ctk.CTkLabel(self, text="Panel de Gestión de Pedidos de Clientes", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_titulo.pack(pady=20)

        # Contenedor con scroll para alojar todas las tarjetas de pedidos
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=850, height=600)
        self.scrollable_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Diccionario para guardar referencias de los widgets (evita perder el foco al escribir)
        self.tarjetas_pedidos = {}

        # Iniciar conexión
        self.conectar_firebase()

    def conectar_firebase(self):
        try:
            ruta_token = os.path.join('keys', 'serviceAccountKey.json')
            cred = credentials.Certificate(ruta_token)
            
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://bbdd-multicanalidad-default-rtdb.europe-west1.firebasedatabase.app/'
                })

            # Arrancamos el listener en el nodo raíz de usuarios
            threading.Thread(target=self.escuchar_pedidos, daemon=True).start()
        except Exception as e:
            print(f"[ERROR] Error conectando a Firebase: {e}")

    def escuchar_pedidos(self):
        ref = db.reference('usuarios')
        ref.listen(self.manejar_evento_firebase)

    def manejar_evento_firebase(self, event):
        # Para evitar lidiar con rutas complejas (ej: /uid/pedidos/pid/estado/2),
        # descargamos el estado completo de forma segura en este hilo secundario.
        usuarios_data = db.reference('usuarios').get()
        
        # Mandamos el árbol completo al hilo principal (Tkinter) para que parsee y dibuje
        self.after(0, self.actualizar_interfaz, usuarios_data)

    def obtener_estado_actual(self, estados_array):
        # Recorre el array de estados desde el final hacia el principio
        # para encontrar el último paso completado (codEstado != 0)
        if not estados_array:
            return "Estado Desconocido"
            
        for est in reversed(estados_array):
            if est and est.get("codEstado", 0) != 0:
                return est.get("descripcion", "Sin descripción")
                
        return "Pedido Recibido (Sin procesar)"

    def actualizar_interfaz(self, usuarios_data):
        pedidos_activos_ids = set()

        if usuarios_data:
            # Recorremos todos los usuarios
            for uid, user_info in usuarios_data.items():
                pedidos = user_info.get("pedidos")
                if pedidos:
                    # Recorremos todos los pedidos de este usuario
                    for pedido_id, pedido_info in pedidos.items():
                        pedidos_activos_ids.add(pedido_id)
                        
                        # Extraer datos principales
                        nombre = pedido_info.get("nombre", "Dispositivo/Plan Desconocido")
                        desc_inicial = pedido_info.get("descripcion", "")
                        estados_array = pedido_info.get("estado", [])
                        estado_actual_str = self.obtener_estado_actual(estados_array)

                        if pedido_id not in self.tarjetas_pedidos:
                            # CREAR NUEVO WIDGET
                            self.crear_tarjeta_pedido(uid, pedido_id, nombre, desc_inicial, estado_actual_str)
                        else:
                            # ACTUALIZAR WIDGET EXISTENTE (Para no destruir la caja de texto en uso)
                            self.tarjetas_pedidos[pedido_id]["lbl_estado"].configure(
                                text=f"📍 Estado Actual: {estado_actual_str}"
                            )

        # Limpiar tarjetas de pedidos que hayan sido borrados de la base de datos
        ids_borrar = set(self.tarjetas_pedidos.keys()) - pedidos_activos_ids
        for pid in ids_borrar:
            self.tarjetas_pedidos[pid]["frame"].destroy()
            del self.tarjetas_pedidos[pid]

    def crear_tarjeta_pedido(self, uid, pedido_id, nombre, desc_inicial, estado_actual_str):
        # Tarjeta (Frame) principal
        frame_pedido = ctk.CTkFrame(self.scrollable_frame, fg_color="#2b2b2b", corner_radius=10)
        frame_pedido.pack(fill="x", pady=10, padx=10)

        # --- SECCIÓN SUPERIOR: DATOS ---
        frame_datos = ctk.CTkFrame(frame_pedido, fg_color="transparent")
        frame_datos.pack(fill="x", padx=15, pady=(15, 5))

        texto_titulo = f"🛒 {nombre}   |   👤 ID Cliente: {uid}\n📝 Detalles: {desc_inicial}"
        label_info = ctk.CTkLabel(frame_datos, text=texto_titulo, justify="left", font=ctk.CTkFont(size=14, weight="bold"))
        label_info.pack(side="left")

        # --- SECCIÓN MEDIA: ESTADO ACTUAL ---
        frame_estado = ctk.CTkFrame(frame_pedido, fg_color="transparent")
        frame_estado.pack(fill="x", padx=15, pady=5)

        label_estado = ctk.CTkLabel(frame_estado, text=f"📍 Estado Actual: {estado_actual_str}", text_color="#1c9aa5", font=ctk.CTkFont(size=13, slant="italic"))
        label_estado.pack(side="left")

        # --- SECCIÓN INFERIOR: ACCIONES DE LOGÍSTICA ---
        frame_acciones = ctk.CTkFrame(frame_pedido, fg_color="transparent")
        frame_acciones.pack(fill="x", padx=15, pady=(5, 15))

        # Desplegable para seleccionar el siguiente paso lógico
        combo_estado = ctk.CTkOptionMenu(frame_acciones, values=[
            "1 - En preparación",
            "2 - Enviado",
            "3 - En reparto",
            "4 - Entregado"
        ], width=160)
        combo_estado.pack(side="left", padx=(0, 10))

        # Input de texto para la descripción
        entry_desc = ctk.CTkEntry(frame_acciones, placeholder_text="Añadir descripción o tracking de envío...", width=300)
        entry_desc.pack(side="left", padx=10, expand=True, fill="x")

        # Botón de actualización
        btn_actualizar = ctk.CTkButton(frame_acciones, text="Actualizar Estado", 
                                   fg_color="#1c9aa5", hover_color="#14767f",
                                   font=ctk.CTkFont(weight="bold"),
                                   command=lambda p_id=pedido_id, u_id=uid, cb=combo_estado, ent=entry_desc: self.actualizar_estado_pedido(u_id, p_id, cb.get(), ent.get()))
        btn_actualizar.pack(side="right", padx=(10, 0))

        # Guardar en memoria
        self.tarjetas_pedidos[pedido_id] = {
            "frame": frame_pedido,
            "lbl_estado": label_estado
        }

    def actualizar_estado_pedido(self, uid, pedido_id, seleccion_combo, descripcion_custom):
        try:
            # Extraemos el número del índice de la cadena del combo (Ej: de "2 - Enviado" sacamos un 2)
            # Como tu array Angular deja libre de la posición 1 a la 4, encaja perfecto.
            index_str = seleccion_combo.split(" ")[0]
            index_int = int(index_str)
            
            texto_defecto = seleccion_combo.split("-")[1].strip()
            
            # Si el trabajador no escribe nada, usamos el texto por defecto del desplegable
            descripcion_final = descripcion_custom if descripcion_custom.strip() else texto_defecto
            
            # Actualizamos directamente la posición del array correspondiente en Firebase
            ruta_estado = f'usuarios/{uid}/pedidos/{pedido_id}/estado/{index_int}'
            
            db.reference(ruta_estado).update({
                "codEstado": index_int + 1,  # Código de avance para que el frontend Angular lo reconozca
                "descripcion": descripcion_final
            })
            
            print(f"[INFO] Pedido {pedido_id} actualizado a: {descripcion_final}")
            
        except Exception as e:
            print(f"[ERROR] Fallo al actualizar el pedido: {e}")

if __name__ == "__main__":
    app = AppEnvios()
    app.mainloop()