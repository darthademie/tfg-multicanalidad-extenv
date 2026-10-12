import customtkinter as ctk
import firebase_admin
from firebase_admin import credentials, db
import threading
import os

# Gestión de ficheros
from pathlib import Path

# Configuración visual moderna de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AppEnvios(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("📦 Envíos 53 - Panel de Logística")
        self.geometry("950x700")
        self.minsize(800, 500)

        self.label_titulo = ctk.CTkLabel(self, text="Panel de Gestión de Pedidos de Clientes", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_titulo.pack(pady=(20, 15))

        # --- NUEVO: BARRA DE BÚSQUEDA ---
        self.frame_buscador = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_buscador.pack(padx=20, pady=(0, 10), fill="x")

        self.entry_busqueda = ctk.CTkEntry(self.frame_buscador, placeholder_text="🔍 Buscar por ID de Cliente...", height=35)
        self.entry_busqueda.pack(side="left", fill="x", expand=True, padx=(0, 10))
        # Vinculamos el evento de teclear (KeyRelease) a la función de filtrar
        self.entry_busqueda.bind("<KeyRelease>", self.filtrar_pedidos)

        self.btn_limpiar = ctk.CTkButton(self.frame_buscador, text="Limpiar", width=80, command=self.limpiar_busqueda)
        self.btn_limpiar.pack(side="right")
        # --------------------------------

        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=850, height=600)
        self.scrollable_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.tarjetas_pedidos = {}
        self.conectar_firebase()

    def conectar_firebase(self):
        try:
            script_dir = Path(__file__).parent
            ruta_token = os.path.join(f"{script_dir}./keys", 'serviceAccountKey.json')
            cred = credentials.Certificate(ruta_token)
            
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://bbdd-multicanalidad-default-rtdb.europe-west1.firebasedatabase.app/'
                })

            threading.Thread(target=self.escuchar_pedidos, daemon=True).start()
        except Exception as e:
            print(f"[ERROR] Error conectando a Firebase: {e}")

    def escuchar_pedidos(self):
        ref = db.reference('usuarios')
        ref.listen(self.manejar_evento_firebase)

    def manejar_evento_firebase(self, event):
        usuarios_data = db.reference('usuarios').get()
        self.after(0, self.actualizar_interfaz, usuarios_data)

    def obtener_estado_actual(self, estados_array):
        if not estados_array:
            return "Estado Desconocido"
            
        # 1. Buscamos primero cuál es el estado Activo (2)
        for est in estados_array:
            if est and est.get("codEstado") == 2:
                return est.get("descripcion", "Sin descripción")
                
        # 2. Si no hay ninguno activo, buscamos el último completado (1) como fallback
        for est in reversed(estados_array):
            if est and est.get("codEstado") == 1:
                return est.get("descripcion", "Completado")
                
        return "Pedido Recibido (Sin procesar)"

    def actualizar_interfaz(self, usuarios_data):
        pedidos_activos_ids = set()

        if usuarios_data:
            for uid, user_info in usuarios_data.items():
                pedidos = user_info.get("pedidos")
                if pedidos:
                    for pedido_id, pedido_info in pedidos.items():
                        pedidos_activos_ids.add(pedido_id)
                        
                        nombre = pedido_info.get("nombre", "Dispositivo/Plan Desconocido")
                        desc_inicial = pedido_info.get("descripcion", "")
                        estados_array = pedido_info.get("estado", [])
                        estado_actual_str = self.obtener_estado_actual(estados_array)
                        
                        # Fix de texto cortado: añadimos espacios al final
                        nuevo_texto_estado = f"📍 Estado Actual: {estado_actual_str}   "

                        if pedido_id not in self.tarjetas_pedidos:
                            self.crear_tarjeta_pedido(uid, pedido_id, nombre, desc_inicial, nuevo_texto_estado)
                        else:
                            # Fix Screen Tear: Solo redibujamos si el texto realmente ha cambiado
                            texto_actual = self.tarjetas_pedidos[pedido_id]["lbl_estado"].cget("text")
                            if texto_actual != nuevo_texto_estado:
                                self.tarjetas_pedidos[pedido_id]["lbl_estado"].configure(text=nuevo_texto_estado)

        ids_borrar = set(self.tarjetas_pedidos.keys()) - pedidos_activos_ids
        for pid in ids_borrar:
            self.tarjetas_pedidos[pid]["frame"].destroy()
            del self.tarjetas_pedidos[pid]

        # Aplicamos el filtro por si entra un pedido nuevo mientras buscamos
        self.filtrar_pedidos()

    def crear_tarjeta_pedido(self, uid, pedido_id, nombre, desc_inicial, estado_actual_str):
        frame_pedido = ctk.CTkFrame(self.scrollable_frame, fg_color="#2b2b2b", corner_radius=10)
        frame_pedido.pack(fill="x", pady=10, padx=10)

        frame_datos = ctk.CTkFrame(frame_pedido, fg_color="transparent")
        frame_datos.pack(fill="x", padx=15, pady=(15, 5))

        texto_titulo = f"🛒 {nombre}   |   👤 ID Cliente: {uid}\n📝 Detalles: {desc_inicial}"
        label_info = ctk.CTkLabel(frame_datos, text=texto_titulo, justify="left", font=ctk.CTkFont(size=14, weight="bold"))
        label_info.pack(side="left")

        frame_estado = ctk.CTkFrame(frame_pedido, fg_color="transparent")
        frame_estado.pack(fill="x", padx=15, pady=5)

        # Usamos el texto ya corregido con espacios finales
        label_estado = ctk.CTkLabel(frame_estado, text=estado_actual_str, text_color="#1c9aa5", font=ctk.CTkFont(size=13, slant="italic"))
        label_estado.pack(side="left")

        frame_acciones = ctk.CTkFrame(frame_pedido, fg_color="transparent")
        frame_acciones.pack(fill="x", padx=15, pady=(5, 15))

        combo_estado = ctk.CTkOptionMenu(frame_acciones, values=[
            "1 - En preparación",
            "2 - Enviado",
            "3 - En el centro de destino",
            "4 - En reparto",
            "5 - Entregado"
        ], width=210)
        combo_estado.pack(side="left", padx=(0, 10))

        entry_desc = ctk.CTkEntry(frame_acciones, placeholder_text="Añadir descripción o tracking de envío...", width=300)
        entry_desc.pack(side="left", padx=10, expand=True, fill="x")

        btn_actualizar = ctk.CTkButton(frame_acciones, text="Actualizar Estado", 
                                   fg_color="#1c9aa5", hover_color="#14767f",
                                   font=ctk.CTkFont(weight="bold"),
                                   command=lambda p_id=pedido_id, u_id=uid, cb=combo_estado, ent=entry_desc: self.actualizar_estado_pedido(u_id, p_id, cb.get(), ent.get()))
        btn_actualizar.pack(side="right", padx=(10, 0))

        # Guardamos la UID en la memoria del diccionario para facilitar la búsqueda
        self.tarjetas_pedidos[pedido_id] = {
            "frame": frame_pedido,
            "lbl_estado": label_estado,
            "uid": str(uid)
        }

    # --- NUEVAS FUNCIONES DE FILTRADO ---
    def filtrar_pedidos(self, event=None):
        termino = self.entry_busqueda.get().strip().lower()
        
        for pid, info in self.tarjetas_pedidos.items():
            if termino in info["uid"].lower():
                # Si coincide, lo mostramos (solo si no estaba ya visible para evitar saltos)
                if not info["frame"].winfo_ismapped():
                    info["frame"].pack(fill="x", pady=10, padx=10)
            else:
                # Si no coincide, lo ocultamos visualmente
                if info["frame"].winfo_ismapped():
                    info["frame"].pack_forget()

    def limpiar_busqueda(self):
        # Borra el texto, devuelve el foco y restaura la vista
        self.entry_busqueda.delete(0, 'end')
        self.filtrar_pedidos()
    # ------------------------------------

    def actualizar_estado_pedido(self, uid, pedido_id, seleccion_combo, descripcion_custom):
        try:
            # 1. Extraemos el índice seleccionado (Ej: "3" de "3 - En reparto") y le restamos 1 para el array
            index_int = int(seleccion_combo.split(" ")[0]) - 1
            texto_defecto = seleccion_combo.split("-")[1].strip()
            
            descripcion_final = descripcion_custom if descripcion_custom.strip() else texto_defecto
            
            ruta_estado = f'usuarios/{uid}/pedidos/{pedido_id}/estado'
            
            # 2. Leemos el array de estados actual de Firebase
            estados_actuales = db.reference(ruta_estado).get()
            
            # Inicialización de seguridad (si falta o viene mal formateado)
            if not estados_actuales:
                estados_actuales = [{"codEstado": 0, "descripcion": ""} for _ in range(5)]
            elif isinstance(estados_actuales, dict):
                estados_actuales = [estados_actuales.get(str(i), {"codEstado": 0, "descripcion": ""}) for i in range(5)]
            
            while len(estados_actuales) < 5:
                estados_actuales.append({"codEstado": 0, "descripcion": ""})

            # 3. APLICAMOS LA LÓGICA DE SEMÁFORO
            for i in range(5):
                if i < index_int:
                    estados_actuales[i]["codEstado"] = 1
                elif i == index_int:
                    estados_actuales[i]["codEstado"] = 2
                    estados_actuales[i]["descripcion"] = descripcion_final
                else:
                    estados_actuales[i]["codEstado"] = 0
            
            # 4. Volcamos el array completo y arreglado a Firebase
            db.reference(ruta_estado).set(estados_actuales)
            
            print(f"[INFO] Pedido {pedido_id} actualizado al paso {index_int + 1}.")
            
            # Limpiamos el entry de descripción una vez actualizado
            self.focus()
            
        except Exception as e:
            print(f"[ERROR] Fallo al actualizar el pedido: {e}")

if __name__ == "__main__":
    app = AppEnvios()
    app.mainloop()