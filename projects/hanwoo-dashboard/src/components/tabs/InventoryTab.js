'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { createInventoryFormValues, inventoryItemSchema } from '@/lib/formSchemas';

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
        <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--color-text)' }}>재고 관리</div>
        <button
          type="button"
          onClick={toggleAddForm}
          style={{
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--color-success)',
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-success)',
            borderRadius: '8px',
            padding: '6px 12px',
            cursor: 'pointer',
          }}
        >
          {isAdding ? '취소' : '+재고 등록'}
        </button>
      </div>

      {isAdding ? (
        <form
          onSubmit={handleSubmit(submitNewItem)}
          style={{
            background: 'var(--color-bg)',
            borderRadius: '14px',
            padding: '16px',
            marginBottom: '16px',
            border: '1px solid var(--color-border)',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px', color: 'var(--color-text)' }}>새 재고 등록</div>
          <div style={{ display: 'grid', gap: '10px' }}>
            <div>
              <input
                placeholder="자재명 (예: 볏짚)"
                {...register('name')}
                style={{
                  width: '100%',
                  padding: '10px',
                  borderRadius: '8px',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-bg-card)',
                  color: 'var(--color-text)',
                }}
              />
              {errors.name ? <div style={errorTextStyle}>{errors.name.message}</div> : null}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <select
                  {...register('category')}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-bg-card)',
                    color: 'var(--color-text)',
                  }}
                >
                  <option value="Feed">사료/조사료</option>
                  <option value="Medicine">약품/영양제</option>
                  <option value="Equipment">기자재</option>
                  <option value="Other">기타</option>
                </select>
                {errors.category ? <div style={errorTextStyle}>{errors.category.message}</div> : null}
              </div>

              <div>
                <input
                  type="number"
                  placeholder="수량"
                  {...register('quantity')}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-bg-card)',
                    color: 'var(--color-text)',
                  }}
                />
                {errors.quantity ? <div style={errorTextStyle}>{errors.quantity.message}</div> : null}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <input
                  placeholder="단위 (예: kg, 박스)"
                  {...register('unit')}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-bg-card)',
                    color: 'var(--color-text)',
                  }}
                />
                {errors.unit ? <div style={errorTextStyle}>{errors.unit.message}</div> : null}
              </div>

              <div>
                <input
                  type="number"
                  placeholder="경고 기준값 (선택)"
                  {...register('threshold')}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-bg-card)',
                    color: 'var(--color-text)',
                  }}
                />
                {errors.threshold ? <div style={errorTextStyle}>{errors.threshold.message}</div> : null}
              </div>
            </div>

            <button
              type="submit"
              style={{
                width: '100%',
                padding: '12px',
                background: 'var(--color-success)',
                color: 'white',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 700,
                marginTop: '8px',
                cursor: 'pointer',
              }}
            >
              등록하기
            </button>
          </div>
        </form>
      ) : null}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {inventory.map((item) => {
          const isLow = item.threshold && item.quantity <= item.threshold;

          return (
            <div
              key={item.id}
              style={{
                background: 'var(--color-bg-card)',
                borderRadius: '14px',
                padding: '14px',
                border: isLow ? '2px solid var(--color-danger)' : '1px solid var(--color-border)',
                position: 'relative',
              }}
            >
              {isLow ? (
                <div
                  style={{
                    position: 'absolute',
                    top: '-8px',
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
                      <input
                        type="number"
                        value={editQty}
                        onChange={(event) => setEditQty(event.target.value)}
                        style={{
                          width: '60px',
                          padding: '4px',
                          fontSize: '14px',
                          background: 'var(--color-bg)',
                          color: 'var(--color-text)',
                          border: '1px solid var(--color-border)',
                          borderRadius: '4px',
                        }}
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={() => handleUpdate(item.id)}
                        style={{
                          background: 'var(--color-success)',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '4px 8px',
                        }}
                      >
                        OK
                      </button>
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
            </div>
          );
        })}

        {inventory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-muted)' }}>등록된 재고가 없습니다.</div>
        ) : null}
      </div>
    </div>
  );
}
