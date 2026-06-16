import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ORDER_TYPES, ORDER_CATEGORIES } from '../data/orderTypes'
import { formatVND } from '../utils/feeCalculator'

export default function CreateOrder() {
  const navigate = useNavigate()
  const [selectedCategory, setSelectedCategory] = useState('phone')
  const [selectedOrderType, setSelectedOrderType] = useState(ORDER_TYPES[0])
  const [recipient, setRecipient] = useState('')
  const [rawAmount, setRawAmount] = useState('')
  const [errors, setErrors] = useState({})

  const filteredTypes = ORDER_TYPES.filter(t => t.category === selectedCategory)

  function handleAmountInput(e) {
    const digits = e.target.value.replace(/\D/g, '')
    setRawAmount(digits)
  }

  function validate() {
    const errs = {}
    if (!recipient.trim()) errs.recipient = 'Vui lòng nhập thông tin'
    if (!rawAmount || parseInt(rawAmount) < 1000) errs.amount = 'Số tiền tối thiểu 1.000đ'
    return errs
  }

  function handleSubmit(e) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    navigate('/cashier', {
      state: {
        orderType: selectedOrderType,
        recipient: recipient.trim(),
        amount: parseInt(rawAmount),
      },
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-slate-50">
      <div className="max-w-[430px] mx-auto min-h-screen flex flex-col">

        {/* Header */}
        <div className="px-5 pt-12 pb-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-primary-600 flex items-center justify-center text-white text-lg shadow-sm">
              💜
            </div>
            <span className="text-xs font-semibold text-primary-600 tracking-widest uppercase">Cashier</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mt-4">Tạo đơn hàng</h1>
          <p className="text-sm text-slate-400 mt-1">Chọn dịch vụ và điền thông tin</p>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col px-4 gap-5 pb-8">

          {/* Service Type */}
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Loại dịch vụ</p>

            {/* Category tabs */}
            <div className="flex gap-2 overflow-x-auto pb-2 no-scrollbar mb-3">
              {ORDER_CATEGORIES.map(cat => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => {
                    setSelectedCategory(cat.id)
                    const first = ORDER_TYPES.find(t => t.category === cat.id)
                    if (first) setSelectedOrderType(first)
                  }}
                  className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    selectedCategory === cat.id
                      ? 'bg-primary-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                  }`}
                >
                  <span>{cat.icon}</span>
                  <span>{cat.name}</span>
                </button>
              ))}
            </div>

            {/* Service items */}
            <div className="grid grid-cols-2 gap-2">
              {filteredTypes.map(type => (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => setSelectedOrderType(type)}
                  className={`text-left p-3 rounded-xl border transition-all ${
                    selectedOrderType.id === type.id
                      ? 'border-primary-500 bg-primary-50 shadow-sm'
                      : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-base mb-2"
                    style={{ backgroundColor: type.color + '20' }}
                  >
                    {type.icon}
                  </div>
                  <p className={`text-xs font-medium leading-tight ${
                    selectedOrderType.id === type.id ? 'text-primary-700' : 'text-slate-600'
                  }`}>{type.name}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Recipient Info */}
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              {selectedOrderType.recipientLabel}
            </label>
            <input
              type="text"
              value={recipient}
              onChange={e => { setRecipient(e.target.value); setErrors(p => ({ ...p, recipient: null })) }}
              placeholder={selectedOrderType.recipientPlaceholder}
              className={`w-full text-base font-medium text-slate-700 placeholder-slate-300 bg-slate-50 rounded-xl px-4 py-3 outline-none focus:ring-2 transition-all ${
                errors.recipient ? 'ring-2 ring-red-300 bg-red-50' : 'focus:ring-primary-300 focus:bg-white'
              }`}
            />
            {errors.recipient && <p className="text-xs text-red-500 mt-1.5">{errors.recipient}</p>}
          </div>

          {/* Amount */}
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Số tiền
            </label>
            <div className={`flex items-center gap-2 bg-slate-50 rounded-xl px-4 py-3 transition-all ${
              errors.amount ? 'ring-2 ring-red-300 bg-red-50' : 'focus-within:ring-2 focus-within:ring-primary-300 focus-within:bg-white'
            }`}>
              <input
                type="text"
                inputMode="numeric"
                value={rawAmount ? formatVND(parseInt(rawAmount)) : ''}
                onChange={handleAmountInput}
                placeholder="0"
                className="flex-1 text-xl font-bold text-slate-800 placeholder-slate-300 bg-transparent outline-none amount-text"
              />
              <span className="text-sm font-semibold text-slate-400">đ</span>
            </div>
            {errors.amount && <p className="text-xs text-red-500 mt-1.5">{errors.amount}</p>}

            {/* Quick amounts */}
            <div className="flex gap-2 mt-3 flex-wrap">
              {[50000, 100000, 200000, 500000].map(amt => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => { setRawAmount(String(amt)); setErrors(p => ({ ...p, amount: null })) }}
                  className="px-3 py-1.5 rounded-full bg-primary-50 text-primary-700 text-xs font-semibold hover:bg-primary-100 transition-colors"
                >
                  {formatVND(amt)}đ
                </button>
              ))}
            </div>
          </div>

          <div className="mt-auto pt-2">
            <button
              type="submit"
              className="w-full py-4 rounded-2xl bg-primary-600 hover:bg-primary-700 active:bg-primary-800 text-white font-bold text-base shadow-lg shadow-primary-200 transition-all flex items-center justify-center gap-2"
            >
              <span>Xem thanh toán</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
