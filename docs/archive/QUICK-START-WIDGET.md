# Quick Start - Widget Integration

## ✅ Todo está listo

La integración del widget está completa y funcional. Sigue estos pasos para probarlo:

---

## 🚀 Paso 1: Iniciar Next.js Frontend

En una terminal:

```bash
cd /Users/qohatpretel/Answering/kb-rag-agent/fe
npm run dev
```

Espera a que aparezca:
```
✓ Ready in 2.1s
○ Local:        http://localhost:3000
```

---

## 🚀 Paso 2: Iniciar Angular App

En **otra terminal**:

```bash
cd /Users/qohatpretel/Answering/REP_FE_COLPENSIONES
npm run start-dev
```

Espera a que compile y abra el navegador automáticamente en `http://localhost:4200` (o el puerto configurado).

---

## ✅ Paso 3: Verificar el Widget

1. **Verifica el botón flotante**
   - En la esquina inferior derecha deberías ver un botón circular morado con icono de chat
   - Si no lo ves, revisa la consola del navegador para errores

2. **Abre el widget**
   - Haz click en el botón flotante
   - El widget debería deslizarse hacia arriba con una animación

3. **Verifica la conexión**
   - Deberías ver un punto de estado (inicialmente naranja/amarillo, luego verde cuando conecte)
   - Si se queda en "Initializing widget...", abre las DevTools y revisa la consola

4. **Prueba el chat**
   - Escribe un mensaje y envíalo
   - Deberías ver tu mensaje y la respuesta del asistente
   - La respuesta debe estar formateada con markdown

---

## 🐛 Troubleshooting

### Widget no aparece
**Solución:**
```bash
# Verifica que Next.js esté corriendo
curl http://localhost:3000/widget
# Debe responder con HTML
```

### "Initializing widget..." permanente
**Problema:** El iframe no está cargando o hay un error de CORS

**Solución:**
1. Abre DevTools (F12) → Console
2. Busca errores de postMessage o iframe
3. Verifica que Next.js esté en http://localhost:3000

**Logs esperados en la consola:**
```
[Angular] Widget loaded, sending INIT message
[Widget] Received INIT message from parent: {...}
[Angular] Widget ready
```

### Widget abre pero no conecta
**Problema:** WebSocket no puede conectarse

**Solución:**
1. Verifica que el backend WebSocket esté corriendo
2. Abre DevTools → Network → WS tab
3. Verifica la URL del WebSocket:
   ```
   wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev
   ```

### Error de compilación en Angular
**Solución:**
```bash
cd /Users/qohatpretel/Answering/REP_FE_COLPENSIONES
rm -rf node_modules package-lock.json
npm install
npm run start-dev
```

---

## 🔧 Configuración de Auth (Opcional)

Si quieres probar con autenticación:

1. Abre la aplicación Angular en el navegador
2. Abre DevTools Console (F12)
3. Ejecuta:
   ```javascript
   sessionStorage.setItem('authToken', 'test-token-123');
   sessionStorage.setItem('userId', 'user-456');
   ```
4. Refresca la página
5. Abre el widget
6. En DevTools Console verás:
   ```
   [Angular] Sending INIT message with config: {
     authToken: "test-token-123",
     userId: "user-456",
     ...
   }
   ```

---

## 📋 Verificación Completa

### ✅ Checklist de Funcionalidad

- [ ] Next.js corre en http://localhost:3000
- [ ] Angular corre en http://localhost:4200
- [ ] Botón flotante visible en esquina inferior derecha
- [ ] Widget abre con animación suave
- [ ] Indicador de conexión cambia de naranja a verde
- [ ] Puedes enviar mensajes
- [ ] Recibes respuestas del asistente
- [ ] Respuestas están formateadas (markdown)
- [ ] Widget se cierra correctamente

### 🎯 Test de Comunicación

Para verificar que la comunicación postMessage funciona:

1. Abre DevTools Console
2. Deberías ver estos logs en orden:
   ```
   [Angular] Widget loaded, sending INIT message
   [Widget] Received INIT message from parent: {...}
   [Angular] Widget ready
   [Angular] User sent message: {...}
   [Angular] Assistant responded: {...}
   ```

---

## 📁 Archivos Modificados

### Next.js Frontend
- ✅ `fe/hooks/useWebSocketChat.ts` - Soporte para config y callbacks
- ✅ `fe/components/chat.tsx` - Acepta prop config
- ✅ `fe/app/widget/page.tsx` - Página widget con postMessage

### Angular App
- ✅ `src/app/app.module.ts` - Importa FuryChatWidgetModule
- ✅ `src/app/app.component.html` - Incluye <fury-chat-widget>
- ✅ `src/app/shared/components/fury-chat-widget/` - Componente completo

---

## 🌐 URLs de Prueba

| Servicio | URL | Propósito |
|----------|-----|-----------|
| Next.js Standalone | http://localhost:3000 | Chat standalone |
| Next.js Widget | http://localhost:3000/widget | Widget embebido (verás loading) |
| Angular App | http://localhost:4200 | App principal con widget |

---

## 💡 Siguiente Paso (Producción)

Cuando estés listo para producción:

1. **Deploy Next.js** (ejemplo: Vercel)
   ```bash
   cd /Users/qohatpretel/Answering/kb-rag-agent/fe
   vercel deploy
   # Obtén URL: https://tu-app.vercel.app
   ```

2. **Actualiza URL en Angular**
   ```typescript
   // app.component.html
   <fury-chat-widget
     [widgetUrl]="'https://tu-app.vercel.app/widget'"
   ></fury-chat-widget>
   ```

3. **Seguridad: Valida Orígenes**
   - Edita `fury-chat-widget.component.ts` línea ~30
   - Edita `fe/app/widget/page.tsx` línea ~23
   - Reemplaza `'*'` con tu dominio real

---

## 📞 Ayuda Adicional

**Documentación completa:**
- `fe/WIDGET-INTEGRATION.md` - Guía técnica completa
- `REP_FE_COLPENSIONES/src/app/shared/components/fury-chat-widget/README.md` - Docs del componente
- `REP_FE_COLPENSIONES/src/app/shared/components/fury-chat-widget/INTEGRATION-EXAMPLE.md` - Ejemplos

**Problema no resuelto?**
Revisa los logs en:
- Browser DevTools → Console (errores JavaScript)
- Browser DevTools → Network → WS (conexión WebSocket)
- Terminal Next.js (errores del servidor)
- Terminal Angular (errores de compilación)
