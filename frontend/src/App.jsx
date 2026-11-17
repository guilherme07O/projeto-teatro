import { useEffect, useMemo, useState } from 'react'

const API = '/api'

function formatExpiry(value) {
  if (!value) return null
  try {
    const date = new Date(value)
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return null
  }
}

export default function App() {
  const [seats, setSeats] = useState([])
  const [userId, setUserId] = useState(() => `user-${Math.floor(Math.random() * 10000)}`)
  const [notice, setNotice] = useState(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  async function loadSeats(silent = false) {
    if (!silent) setRefreshing(true)
    try {
      const res = await fetch(`${API}/seats`)
      const data = await res.json()
      setSeats(Array.isArray(data) ? data : [])
    } catch (e) {
      setNotice({ type: 'error', text: 'Não foi possível carregar os assentos. Verifique se o backend está ativo.' })
    } finally {
      if (!silent) setRefreshing(false)
    }
  }

  useEffect(() => {
    loadSeats()
    const t = setInterval(() => loadSeats(true), 5000)
    return () => clearInterval(t)
  }, [])

  async function reserve(seat) {
    setLoading(true)
    setNotice(null)
    try {
      const res = await fetch(`${API}/reserve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seat_id: seat.id, user_id: userId }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Não foi possível reservar este assento.')
      const exp = formatExpiry(data.expires_at)
      setNotice({ type: 'success', text: `Assento ${seat.label} reservado com sucesso (reserva #${data.id}).${exp ? ` Expira às ${exp}.` : ''}` })
      await loadSeats(true)
    } catch (e) {
      setNotice({ type: 'error', text: e.message || 'Erro ao reservar assento.' })
    } finally {
      setLoading(false)
    }
  }

  async function pay(seat) {
    if (!seat.reservation_id) return
    setLoading(true)
    setNotice(null)
    try {
      const res = await fetch(`${API}/pay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reservation_id: seat.reservation_id, user_id: userId }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Não foi possível confirmar o pagamento.')
      setNotice({ type: 'success', text: `Pagamento confirmado para o assento ${seat.label} (reserva #${data.id}).` })
      await loadSeats(true)
    } catch (e) {
      setNotice({ type: 'error', text: e.message || 'Erro ao processar pagamento.' })
    } finally {
      setLoading(false)
    }
  }

  function handleSeatClick(seat) {
    if (loading) return
    if (seat.status === 'available') reserve(seat)
    else if (seat.status === 'reserved') pay(seat)
  }

  const summary = useMemo(() => {
    const s = { available: 0, reserved: 0, paid: 0 }
    for (const seat of seats) s[seat.status] = (s[seat.status] || 0) + 1
    return s
  }, [seats])

  const total = seats.length || 300

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">Espetáculo ao vivo • Seleção em tempo real</div>
          <h1>Venda de Ingressos com Assento Marcado</h1>
          <p className="subtitle">
            Escolha seu lugar no mapa, garanta a reserva por 10 minutos e conclua o pagamento simulado.
            Conflitos de concorrência são tratados pelo backend com retorno <strong>409 Conflict</strong>.
          </p>
          <div className="stats">
            <div className="stat available">
              <div className="stat-label">Disponíveis</div>
              <div className="stat-value">{summary.available || 0}</div>
            </div>
            <div className="stat reserved">
              <div className="stat-label">Reservados</div>
              <div className="stat-value">{summary.reserved || 0}</div>
            </div>
            <div className="stat paid">
              <div className="stat-label">Pagos</div>
              <div className="stat-value">{summary.paid || 0}</div>
            </div>
          </div>
        </div>

        <div className="controls panel">
          <h2>Sessão de compra</h2>
          <div className="field">
            <label htmlFor="userId">Identificador do usuário</label>
            <div className="input-row">
              <input
                id="userId"
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="ex.: user-1234"
              />
              <button className="btn primary" onClick={() => loadSeats()} disabled={loading || refreshing}>
                {refreshing ? 'Atualizando...' : 'Atualizar'}
              </button>
            </div>
          </div>
          <p className="hint"><strong>Como usar:</strong> clique em um assento <strong>disponível</strong> para reservar. Clique em um assento <strong>reservado</strong> para simular o pagamento (usando o mesmo usuário da reserva).</p>
          <p className="hint">O mapa é atualizado automaticamente a cada 5 segundos para refletir reservas, pagamentos e expirações.</p>
          <p className="hint">Total de assentos no teatro: <strong>{total}</strong></p>
        </div>
      </section>

      {notice && (
        <div className={`toast ${notice.type === 'error' ? 'error' : 'success'}`}>
          <span>{notice.text}</span>
          <button className="btn" onClick={() => setNotice(null)}>Fechar</button>
        </div>
      )}

      <section className="main-grid">
        <div className="theater panel">
          <div className="theater-header">
            <h2>Mapa de assentos</h2>
            <div className="legend">
              <span><i className="dot available" /> Disponível</span>
              <span><i className="dot reserved" /> Reservado</span>
              <span><i className="dot paid" /> Pago</span>
            </div>
          </div>

          <div className="stage-wrap"><div className="stage">Palco</div></div>

          <div className="seats-grid">
            {seats.map((seat) => {
              const exp = formatExpiry(seat.expires_at)
              const actionable = seat.status === 'available' || seat.status === 'reserved'
              return (
                <button
                  key={seat.id}
                  className={`seat ${seat.status}`}
                  onClick={() => handleSeatClick(seat)}
                  disabled={loading || !actionable}
                  title={
                    seat.status === 'reserved' && exp
                      ? `Reservado • expira às ${exp} • clique para pagar`
                      : seat.status === 'available'
                      ? 'Disponível • clique para reservar'
                      : 'Assento pago'
                  }
                >
                  <span>{seat.label}</span>
                  {seat.status === 'reserved' && exp && <span className="sub">{exp}</span>}
                </button>
              )
            })}
          </div>

          <div className="footer-note">
            Dica: para a demonstração de concorrência, execute o Locust com 100 usuários no mesmo assento e observe que apenas uma requisição obtém sucesso.
          </div>
        </div>
      </section>
    </div>
  )
}
