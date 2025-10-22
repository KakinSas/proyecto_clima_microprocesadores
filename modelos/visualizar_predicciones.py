"""
Script para visualizar las predicciones de temperatura
generadas por predecir_futuro.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent
    pred_path = base_dir / "predicciones_6_horas.csv"
    
    if not pred_path.exists():
        print(f"❌ Archivo de predicciones no encontrado: {pred_path}")
        print(f"\n💡 Primero ejecuta: python predecir_futuro.py")
        return
    
    # Cargar predicciones
    df = pd.read_csv(pred_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"✅ Cargadas {len(df):,} predicciones")
    print(f"   Desde: {df['timestamp'].iloc[0]}")
    print(f"   Hasta: {df['timestamp'].iloc[-1]}")
    
    # Crear visualizaciones
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # 1. Serie temporal completa
    ax1 = axes[0, 0]
    ax1.plot(df['horas_desde_inicio'], df['temperatura_predicha'], 
             linewidth=1.5, color='#e74c3c', alpha=0.8)
    ax1.set_xlabel('Horas desde ahora', fontsize=11)
    ax1.set_ylabel('Temperatura (°C)', fontsize=11)
    ax1.set_title('📈 Predicción de Temperatura - Próximas 6 Horas', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=df['temperatura_predicha'].mean(), color='blue', 
                linestyle='--', alpha=0.5, label=f'Media: {df["temperatura_predicha"].mean():.2f}°C')
    ax1.legend()
    
    # 2. Primeros 30 minutos (detalle)
    ax2 = axes[0, 1]
    df_30min = df[df['minutos_desde_inicio'] <= 30]
    ax2.plot(df_30min['minutos_desde_inicio'], df_30min['temperatura_predicha'],
             linewidth=2, color='#3498db', marker='o', markersize=1, alpha=0.8)
    ax2.set_xlabel('Minutos desde ahora', fontsize=11)
    ax2.set_ylabel('Temperatura (°C)', fontsize=11)
    ax2.set_title('🔍 Detalle: Primeros 30 Minutos', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 3. Distribución de temperaturas
    ax3 = axes[1, 0]
    ax3.hist(df['temperatura_predicha'], bins=50, color='#2ecc71', alpha=0.7, edgecolor='black')
    ax3.axvline(df['temperatura_predicha'].mean(), color='red', 
                linestyle='--', linewidth=2, label=f'Media: {df["temperatura_predicha"].mean():.2f}°C')
    ax3.set_xlabel('Temperatura (°C)', fontsize=11)
    ax3.set_ylabel('Frecuencia', fontsize=11)
    ax3.set_title('📊 Distribución de Temperaturas Predichas', fontsize=13, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Cambio acumulado
    ax4 = axes[1, 1]
    temp_inicial = df['temperatura_predicha'].iloc[0]
    cambios = df['temperatura_predicha'] - temp_inicial
    ax4.plot(df['horas_desde_inicio'], cambios, 
             linewidth=1.5, color='#9b59b6', alpha=0.8)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax4.set_xlabel('Horas desde ahora', fontsize=11)
    ax4.set_ylabel('Cambio de Temperatura (°C)', fontsize=11)
    ax4.set_title(f'📉 Cambio Acumulado (ref: {temp_inicial:.2f}°C)', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.fill_between(df['horas_desde_inicio'], cambios, 0, 
                      where=(cambios >= 0), alpha=0.3, color='red', label='Aumento')
    ax4.fill_between(df['horas_desde_inicio'], cambios, 0, 
                      where=(cambios < 0), alpha=0.3, color='blue', label='Disminución')
    ax4.legend()
    
    plt.tight_layout()
    
    # Guardar gráfica
    output_img = base_dir / "predicciones_6_horas.png"
    plt.savefig(output_img, dpi=150, bbox_inches='tight')
    print(f"\n💾 Gráfica guardada en: {output_img.name}")
    
    plt.show()
    
    # Resumen estadístico por hora
    print(f"\n📊 RESUMEN POR HORA:")
    print(f"\n{'Hora':<10} {'Temp Min':<12} {'Temp Max':<12} {'Temp Prom':<12} {'Cambio':<12}")
    print("-" * 60)
    
    temp_inicial = df['temperatura_predicha'].iloc[0]
    for hora in range(7):
        if hora == 0:
            df_hora = df[df['minutos_desde_inicio'] < 60]
            label = "0-1h"
        else:
            df_hora = df[(df['horas_desde_inicio'] >= hora-1) & (df['horas_desde_inicio'] < hora)]
            label = f"{hora-1}-{hora}h"
        
        if len(df_hora) > 0:
            temp_min = df_hora['temperatura_predicha'].min()
            temp_max = df_hora['temperatura_predicha'].max()
            temp_prom = df_hora['temperatura_predicha'].mean()
            cambio = temp_prom - temp_inicial
            
            print(f"{label:<10} {temp_min:>10.2f}°C  {temp_max:>10.2f}°C  {temp_prom:>10.2f}°C  {cambio:>+9.2f}°C")
    
    print(f"\n✅ Visualización completada")

if __name__ == "__main__":
    main()
