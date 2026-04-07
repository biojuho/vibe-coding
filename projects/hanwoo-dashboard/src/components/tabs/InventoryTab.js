'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { createInventoryFormValues, inventoryItemSchema } from '@/lib/formSchemas';
import { PremiumButton } from '@/components/ui/premium-button';
import { PremiumInput, PremiumSelect, PremiumLabel } from '@/components/ui/premium-input';
import { PremiumCard, PremiumCardContent } from '@/components/ui/premium-card';

const errorTextStyle = {
  fontSize: '12px',
  marginTop: '6px',
  color: 'var(--color-danger)',
  fontWeight: 600,
};

export default function InventoryTab({ inventory, onAddItem, onUpdateQuantity }) {
  const [isAdding, setIsAdding] = useState(false);
  const [editId, setEditId] = useState(null);
  const [editQty, setEditQty] = useState('');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(inventoryItemSchema),
    defaultValues: createInventoryFormValues(),
  });

  const categories = {
    Feed: '사료',
    Medicine: '약품',
    Equipment: '기자재',
    Other: '기타',
  };

  const toggleAddForm = () => {
    const next = !isAdding;
    setIsAdding(next);

    if (!next) {
      reset(createInventoryFormValues());
    }
  };

  const submitNewItem = (values) => {
    onAddItem(values);
    setIsAdding(false);
    reset(createInventoryFormValues());
  };

  const handleUpdate = (id) => {
    if (editQty === '' || Number(editQty) < 0) {
      return;
    }

    onUpdateQuantity(id, editQty);
    setEditId(null);
    setEditQty('');
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '20px', lineHeight: 1 }}>📦</span>
          <span style={{ fontSize: '17px', fontWeight: 800, color: 'var(--color-text)', letterSpacing: '-0.01em' }}>재고 관리</span>
        </div>
        <PremiumButton
          variant="outline"
          size="sm"
          onClick={toggleAddForm}
          className="text-[13px] text-green-400 border-green-500/50 hover:bg-green-500/10 px-3 py-1.5 rounded-lg font-bold"
        >
          {isAdding ? '취소' : '+재고 등록'}
        </PremiumButton>
      </div>

      {isAdding ? (
        <form onSubmit={handleSubmit(submitNewItem)} className="mb-4">
          <PremiumCard className="bg-slate-800/60 w-full mb-4">
            <PremiumCardContent className="p-4">
              <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px', color: 'var(--color-text)' }}>새 재고 등록</div>
              <div style={{ display: 'grid', gap: '10px' }}>
                <div>
                  <PremiumInput
                    placeholder="자재명 (예: 볏짚)"
                    {...register('name')}
                    hasError={!!errors.name}
                  />
                  {errors.name ? <div style={errorTextStyle}>{errors.name.message}</div> : null}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <PremiumSelect
                      {...register('category')}
                      hasError={!!errors.category}
                    >
                      <option value="Feed" className="bg-slate-900">사료/조사료</option>
                      <option value="Medicine" className="bg-slate-900">약품/영양제</option>
                      <option value="Equipment" className="bg-slate-900">기자재</option>
                      <option value="Other" className="bg-slate-900">기타</option>
                    </PremiumSelect>
                    {errors.category ? <div style={errorTextStyle}>{errors.category.message}</div> : null}
                  </div>

                  <div>
                    <PremiumInput
                      type="number"
                      placeholder="수량"
                      {...register('quantity')}
                      hasError={!!errors.quantity}
                    />
                    {errors.quantity ? <div style={errorTextStyle}>{errors.quantity.message}</div> : null}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <PremiumInput
                      placeholder="단위 (예: kg, 박스)"
                      {...register('unit')}
                      hasError={!!errors.unit}
                    />
                    {errors.unit ? <div style={errorTextStyle}>{errors.unit.message}</div> : null}
                  </div>

                  <div>
                    <PremiumInput
                      type="number"
                      placeholder="경고 기준값 (선택)"
                      {...register('threshold')}
                      hasError={!!errors.threshold}
                    />
                    {errors.threshold ? <div style={errorTextStyle}>{errors.threshold.message}</div> : null}
                  </div>
                </div>

                <PremiumButton type="submit" variant="primary" glow className="w-full py-3 mt-2 rounded-lg">
                  등록하기
                </PremiumButton>
              </div>
            </PremiumCardContent>
          </PremiumCard>
        </form>
      ) : null}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {inventory.map((item) => {
          const isLow = item.threshold && item.quantity <= item.threshold;

          return (
            <PremiumCard
              key={item.id}
              className={`p-0 ${isLow ? 'border-2 border-red-500/50' : ''}`}
            >
              <PremiumCardContent className="p-3.5 relative">
                {isLow ? (
                  <div
                    style={{
                      position: 'absolute',
                      top: '-10px',
                      right: '10px',
                      background: 'var(--color-danger)',
                      color: 'white',
                      fontSize: '10px',
                      padding: '2px 8px',
                      borderRadius: '10px',
                      fontWeight: 700,
                    }}
                  >
                    부족 경고
                  </div>
                ) : null}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '2px' }}>
                      {categories[item.category] || item.category}
                    </div>
                    <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--color-text)' }}>{item.name}</div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    {editId === item.id ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <PremiumInput
                          type="number"
                          value={editQty}
                          onChange={(event) => setEditQty(event.target.value)}
                          className="w-[80px] px-2 py-1.5 h-auto text-sm bg-slate-900 border-slate-700"
                          autoFocus
                          hasError={false}
                        />
                        <PremiumButton
                          variant="secondary"
                          onClick={() => handleUpdate(item.id)}
                          className="px-2 py-1.5 h-auto text-xs"
                        >
                          OK
                        </PremiumButton>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setEditId(item.id);
                          setEditQty(String(item.quantity));
                        }}
                        style={{
                          fontSize: '16px',
                          fontWeight: 800,
                          color: isLow ? 'var(--color-danger)' : 'var(--color-text)',
                          cursor: 'pointer',
                          background: 'none',
                          border: 'none',
                          padding: 0,
                        }}
                      >
                        {item.quantity} <span style={{ fontSize: '12px', fontWeight: 400 }}>{item.unit}</span>
                      </button>
                    )}
                  </div>
                </div>
              </PremiumCardContent>
            </PremiumCard>
          );
        })}

        {inventory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-muted)' }}>등록된 재고가 없습니다.</div>
        ) : null}
      </div>
    </div>
  );
}
