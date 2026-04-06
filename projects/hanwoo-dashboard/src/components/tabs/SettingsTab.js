'use client';

import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { MapPin, Settings } from 'lucide-react';
import { PremiumButton } from '@/components/ui/premium-button';
import { PremiumInput, PremiumSelect, PremiumLabel } from '@/components/ui/premium-input';

import { useAppFeedback } from '@/components/feedback/FeedbackProvider';
import {
  buildingFormSchema,
  createBuildingFormValues,
  createFarmSettingsValues,
  farmSettingsSchema,
} from '@/lib/formSchemas';

const errorTextStyle = {
  fontSize: '12px',
  marginTop: '6px',
  color: 'var(--color-danger)',
  fontWeight: 600,
};

export default function SettingsTab({
  buildings,
  onCreateBuilding,
  onDeleteBuilding,
  farmSettings,
  onUpdateFarmSettings,
  theme,
  onToggleTheme,
  widgetRegistry = [],
  widgetVisible = {},
  onToggleWidget,
}) {
  const [isAdding, setIsAdding] = useState(false);
  const { confirm } = useAppFeedback();

  const {
    register: registerBuilding,
    handleSubmit: handleSubmitBuilding,
    reset: resetBuilding,
    formState: { errors: buildingErrors },
  } = useForm({
    resolver: zodResolver(buildingFormSchema),
    defaultValues: createBuildingFormValues(),
  });

  const {
    register: registerFarm,
    handleSubmit: handleSubmitFarm,
    reset: resetFarm,
    setValue: setFarmValue,
    formState: { errors: farmErrors },
  } = useForm({
    resolver: zodResolver(farmSettingsSchema),
    defaultValues: createFarmSettingsValues(farmSettings),
  });

  useEffect(() => {
    resetFarm(createFarmSettingsValues(farmSettings));
  }, [farmSettings, resetFarm]);

  const koreanLocations = useMemo(
    () => [
      { name: '서울', lat: 37.566, lng: 126.978 },
      { name: '부산', lat: 35.179, lng: 129.075 },
      { name: '대구', lat: 35.871, lng: 128.601 },
      { name: '인천', lat: 37.456, lng: 126.705 },
      { name: '광주', lat: 35.16, lng: 126.851 },
      { name: '대전', lat: 36.35, lng: 127.384 },
      { name: '울산', lat: 35.538, lng: 129.311 },
      { name: '세종', lat: 36.48, lng: 127.289 },
      { name: '경기 수원', lat: 37.263, lng: 127.028 },
      { name: '강원 춘천', lat: 37.881, lng: 127.729 },
      { name: '충북 청주', lat: 36.642, lng: 127.489 },
      { name: '충남 홍성', lat: 36.601, lng: 126.66 },
      { name: '전북 전주', lat: 35.824, lng: 127.147 },
      { name: '전북 남원', lat: 35.416, lng: 127.39 },
      { name: '전북 남원 대강', lat: 35.446, lng: 127.344 },
      { name: '전남 무안', lat: 34.99, lng: 126.471 },
      { name: '경북 안동', lat: 36.568, lng: 128.729 },
      { name: '경남 창원', lat: 35.227, lng: 128.681 },
      { name: '제주', lat: 33.499, lng: 126.531 },
    ],
    [],
  );

  const handleLocationSelect = (event) => {
    const selected = koreanLocations.find((location) => location.name === event.target.value);
    if (!selected) {
      return;
    }

    setFarmValue('location', selected.name, { shouldDirty: true, shouldValidate: true });
    setFarmValue('latitude', selected.lat, { shouldDirty: true, shouldValidate: true });
    setFarmValue('longitude', selected.lng, { shouldDirty: true, shouldValidate: true });
  };

  const submitBuilding = (values) => {
    onCreateBuilding(values);
    setIsAdding(false);
    resetBuilding(createBuildingFormValues());
  };

  const submitFarmSettings = (values) => {
    onUpdateFarmSettings(values);
  };

  const handleDeleteBuilding = async (id, name) => {
    const shouldDelete = await confirm({
      title: `${name} 동을 삭제할까요?`,
      description: '연결된 개체가 있으면 삭제되지 않습니다.',
      confirmLabel: '삭제',
      cancelLabel: '취소',
      variant: 'destructive',
    });

    if (!shouldDelete) {
      return;
    }

    onDeleteBuilding(id);
  };

  const isDark = theme === 'dark';

  return (
    <div>
      <div
        style={{
          fontSize: '18px',
          fontWeight: 800,
          color: 'var(--color-text)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '20px',
        }}
      >
        <Settings size={20} /> 환경 설정
      </div>

      <div
        style={{
          background: 'var(--color-bg-card)',
          padding: '18px 20px',
          borderRadius: '16px',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '20px' }}>{isDark ? '야' : '주'}</span>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text)' }}>다크모드</div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              {isDark ? '어두운 화면 사용 중' : '밝은 화면 사용 중'}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onToggleTheme}
          style={{
            width: '52px',
            height: '28px',
            borderRadius: '14px',
            border: 'none',
            cursor: 'pointer',
            position: 'relative',
            background: isDark ? 'var(--color-primary)' : 'var(--color-border)',
            transition: 'background 0.3s ease',
          }}
        >
          <div
            style={{
              width: '22px',
              height: '22px',
              borderRadius: '50%',
              background: 'var(--color-bg-card)',
              position: 'absolute',
              top: '3px',
              left: isDark ? '27px' : '3px',
              transition: 'left 0.3s ease',
              boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
            }}
          />
        </button>
      </div>

      {widgetRegistry.length > 0 ? (
        <div
          style={{
            background: 'var(--color-bg-card)',
            padding: '18px 20px',
            borderRadius: '16px',
            boxShadow: 'var(--shadow-sm)',
            marginBottom: '20px',
          }}
        >
          <div
            style={{
              fontSize: '14px',
              fontWeight: 700,
              color: 'var(--color-text)',
              marginBottom: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span style={{ fontSize: '18px' }}>위젯</span> 대시보드 위젯
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '12px' }}>
            홈 화면에 표시할 위젯을 선택해 주세요.
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {widgetRegistry.map((widget) => {
              const isOn = widgetVisible[widget.id] !== false;

              return (
                <div
                  key={widget.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    borderRadius: '10px',
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '16px' }}>{widget.icon}</span>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)' }}>{widget.label}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onToggleWidget(widget.id)}
                    style={{
                      width: '44px',
                      height: '24px',
                      borderRadius: '12px',
                      border: 'none',
                      cursor: 'pointer',
                      position: 'relative',
                      background: isOn ? 'var(--color-success)' : 'var(--color-border)',
                      transition: 'background 0.3s ease',
                    }}
                  >
                    <div
                      style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        background: 'var(--color-bg-card)',
                        position: 'absolute',
                        top: '3px',
                        left: isOn ? '23px' : '3px',
                        transition: 'left 0.3s ease',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                      }}
                    />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      <form
        onSubmit={handleSubmitFarm(submitFarmSettings)}
        style={{
          background: 'var(--color-bg-card)',
          padding: '20px',
          borderRadius: '16px',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '30px',
        }}
      >
        <div
          style={{
            fontSize: '15px',
            fontWeight: 700,
            marginBottom: '16px',
            color: 'var(--color-text)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <MapPin size={16} /> 농장 정보 설정
        </div>

        <div style={{ display: 'grid', gap: '16px' }}>
          <div>
            <PremiumLabel>
              농장 이름
            </PremiumLabel>
            <PremiumInput
              {...registerFarm('name')}
              placeholder="예: 행복한 한우 농장"
              hasError={!!farmErrors.name}
            />
            {farmErrors.name ? <div style={errorTextStyle}>{farmErrors.name.message}</div> : null}
          </div>

          <div>
            <PremiumLabel>
              지역 선택 (자동 입력)
            </PremiumLabel>
            <PremiumSelect
              onChange={handleLocationSelect}
              className="mb-2"
              hasError={false}
            >
              <option value="" className="bg-slate-900">주요 지역 선택...</option>
              {koreanLocations.map((location) => (
                <option key={location.name} value={location.name} className="bg-slate-900">
                  {location.name}
                </option>
              ))}
            </PremiumSelect>
            <PremiumInput
              {...registerFarm('location')}
              placeholder="지역명을 직접 입력해 주세요."
              hasError={!!farmErrors.location}
            />
            {farmErrors.location ? <div style={errorTextStyle}>{farmErrors.location.message}</div> : null}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <PremiumLabel>
                위도 (Latitude)
              </PremiumLabel>
              <PremiumInput
                type="number"
                step="0.001"
                {...registerFarm('latitude')}
                placeholder="35.446"
                hasError={!!farmErrors.latitude}
              />
              {farmErrors.latitude ? <div style={errorTextStyle}>{farmErrors.latitude.message}</div> : null}
            </div>
            <div>
              <PremiumLabel>
                경도 (Longitude)
              </PremiumLabel>
              <PremiumInput
                type="number"
                step="0.001"
                {...registerFarm('longitude')}
                placeholder="127.344"
                hasError={!!farmErrors.longitude}
              />
              {farmErrors.longitude ? <div style={errorTextStyle}>{farmErrors.longitude.message}</div> : null}
            </div>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
            정확한 날씨 정보를 위해 좌표를 확인해 주세요.
          </div>

          <PremiumButton type="submit" className="w-full mt-1 py-3.5 rounded-[10px]" glow>
            저장하기
          </PremiumButton>

          <div style={{ marginTop: '10px', borderTop: '1px dashed var(--color-border)', paddingTop: '10px', textAlign: 'center' }}>
            <a href="/admin/diagnostics" style={{ fontSize: '12px', color: 'var(--color-text-muted)', textDecoration: 'none' }}>
              시스템 진단 도구
            </a>
          </div>
        </div>
      </form>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-secondary)' }}>축사 동 관리</div>
        <PremiumButton
          variant="secondary"
          size="sm"
          onClick={() => {
            const next = !isAdding;
            setIsAdding(next);
            if (!next) {
              resetBuilding(createBuildingFormValues());
            }
          }}
          className="text-xs px-3 py-1.5 rounded-lg font-bold"
        >
          {isAdding ? '취소' : '+ 동 추가'}
        </PremiumButton>
      </div>

      {isAdding ? (
        <form
          onSubmit={handleSubmitBuilding(submitBuilding)}
          style={{
            background: 'var(--color-bg-card)',
            padding: '20px',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-sm)',
            marginBottom: '20px',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px', color: 'var(--color-text)' }}>새 축사 동 등록</div>
          <div style={{ display: 'grid', gap: '12px' }}>
            <div>
              <PremiumLabel>
                동 이름
              </PremiumLabel>
              <PremiumInput
                {...registerBuilding('name')}
                placeholder="동 이름을 입력해 주세요."
                hasError={!!buildingErrors.name}
              />
              {buildingErrors.name ? <div style={errorTextStyle}>{buildingErrors.name.message}</div> : null}
            </div>

            <div>
              <PremiumLabel>
                칸 수 (Pen Count)
              </PremiumLabel>
              <PremiumInput
                type="number"
                {...registerBuilding('penCount')}
                hasError={!!buildingErrors.penCount}
              />
              {buildingErrors.penCount ? <div style={errorTextStyle}>{buildingErrors.penCount.message}</div> : null}
            </div>

            <PremiumButton type="submit" variant="primary" className="w-full py-3 rounded-lg" glow>
              등록하기
            </PremiumButton>
          </div>
        </form>
      ) : null}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {buildings.map((building) => (
          <div
            key={building.id}
            style={{
              background: 'var(--color-bg-card)',
              padding: '16px',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text)' }}>{building.name}</div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>총 {building.penCount}칸</div>
            </div>
            <PremiumButton
              variant="outline"
              size="sm"
              onClick={() => handleDeleteBuilding(building.id, building.name)}
              className="text-xs text-red-500 border-red-500/50 hover:bg-red-500/10 px-2 py-1 rounded h-auto"
            >
              삭제
            </PremiumButton>
          </div>
        ))}
      </div>
    </div>
  );
}
