export function calculateFees(rules, orderTypeId, paymentMethodId, amount) {
  const applicableRules = rules.filter(rule => {
    if (!rule.enabled) return false

    const { conditions } = rule

    if (conditions.orderTypes !== null && !conditions.orderTypes.includes(orderTypeId)) {
      return false
    }

    if (conditions.paymentMethods !== null && !conditions.paymentMethods.includes(paymentMethodId)) {
      return false
    }

    if (conditions.amountRange !== null) {
      const { min, max } = conditions.amountRange
      if (min !== null && amount < min) return false
      if (max !== null && amount > max) return false
    }

    return true
  })

  const feeItems = applicableRules.map(rule => {
    const { fee } = rule
    let feeAmount = 0

    switch (fee.type) {
      case 'percentage':
        feeAmount = Math.round(amount * fee.value / 100)
        break
      case 'flat':
        feeAmount = fee.value
        break
      case 'percentage_with_min':
        feeAmount = Math.max(Math.round(amount * fee.value / 100), fee.min)
        break
      case 'percentage_with_max':
        feeAmount = Math.min(Math.round(amount * fee.value / 100), fee.max)
        break
      default:
        feeAmount = 0
    }

    return {
      id: rule.id,
      label: fee.displayLabel,
      amount: feeAmount,
    }
  })

  const totalFee = feeItems.reduce((sum, item) => sum + item.amount, 0)

  return {
    items: feeItems,
    total: totalFee,
  }
}

export function formatVND(amount) {
  return new Intl.NumberFormat('vi-VN').format(amount)
}
