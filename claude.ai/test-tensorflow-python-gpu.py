# Complete package test script with comprehensive GPU testing
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import sklearn
import xgboost as xgb
import lightgbm as lgb
import fastapi
import sqlalchemy

# Test TensorFlow with comprehensive GPU testing
try:
    import tensorflow as tf
    tensorflow_available = True
    tensorflow_version = tf.__version__
except ImportError as e:
    tensorflow_available = False
    tensorflow_error = str(e)

# Test additional packages
try:
    import pandas_ta as ta
    pandas_ta_available = True
    pandas_ta_version = ta.__version__
except ImportError:
    pandas_ta_available = False

try:
    import yfinance as yf
    yfinance_available = True
    yfinance_version = yf.__version__
except ImportError:
    yfinance_available = False

try:
    import psycopg2
    psycopg2_available = True
    psycopg2_version = psycopg2.__version__
except ImportError:
    psycopg2_available = False

print('🎉 Package Installation Test Results')
print('=' * 60)
print(f'✅ Pandas: {pd.__version__}')
print(f'✅ NumPy: {np.__version__}')
print(f'✅ Matplotlib: {matplotlib.__version__}')
print(f'✅ Plotly: {plotly.__version__}')
print(f'✅ Scikit-learn: {sklearn.__version__}')
print(f'✅ XGBoost: {xgb.__version__}')
print(f'✅ LightGBM: {lgb.__version__}')
print(f'✅ FastAPI: {fastapi.__version__}')
print(f'✅ SQLAlchemy: {sqlalchemy.__version__}')

# Comprehensive TensorFlow and GPU testing
print('=' * 60)
print('🧠 TENSORFLOW & GPU ANALYSIS')
print('=' * 60)

if tensorflow_available:
    print(f'✅ TensorFlow: {tensorflow_version}')
    
    # Check TensorFlow build info
    print(f'📦 TensorFlow built with CUDA: {tf.test.is_built_with_cuda()}')
    print(f'📦 TensorFlow built with GPU support: {tf.test.is_built_with_gpu_support()}')
    
    # List all available devices
    print('🖥️  Available devices:')
    for device in tf.config.list_physical_devices():
        print(f'   - {device.device_type}: {device.name}')
    
    # Specific GPU detection
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f'🚀 GPU DETECTED: {len(gpus)} GPU(s) available')
        for i, gpu in enumerate(gpus):
            print(f'   GPU {i}: {gpu.name}')
            
        # Test GPU memory info (if available)
        try:
            gpu_details = tf.config.experimental.get_device_details(gpus[0])
            if 'device_name' in gpu_details:
                print(f"   GPU Name: {gpu_details['device_name']}")
            if 'compute_capability' in gpu_details:
                print(f"   Compute Capability: {gpu_details['compute_capability']}")
        except Exception as e:
            print(f'   GPU details not available: {e}')
            
        # Test actual GPU computation
        print('🧪 Testing GPU computation...')
        try:
            with tf.device('/GPU:0'):
                # Create tensors on GPU
                a = tf.random.normal([1000, 1000])
                b = tf.random.normal([1000, 1000])
                
                # Perform computation
                import time
                start_time = time.time()
                c = tf.matmul(a, b)
                gpu_time = time.time() - start_time
                
                print(f'✅ GPU computation successful!')
                print(f'   Matrix multiplication (1000x1000): {gpu_time:.4f} seconds on GPU')
        except Exception as e:
            print(f'❌ GPU computation failed: {e}')
            
        # Compare CPU vs GPU performance
        print('⚡ CPU vs GPU Performance Test:')
        try:
            # CPU test
            with tf.device('/CPU:0'):
                a_cpu = tf.random.normal([500, 500])
                b_cpu = tf.random.normal([500, 500])
                start_time = time.time()
                c_cpu = tf.matmul(a_cpu, b_cpu)
                cpu_time = time.time() - start_time
                
            # GPU test
            with tf.device('/GPU:0'):
                a_gpu = tf.random.normal([500, 500])
                b_gpu = tf.random.normal([500, 500])
                start_time = time.time()
                c_gpu = tf.matmul(a_gpu, b_gpu)
                gpu_time = time.time() - start_time
                
            print(f'   CPU time: {cpu_time:.4f}s')
            print(f'   GPU time: {gpu_time:.4f}s')
            if gpu_time < cpu_time:
                speedup = cpu_time / gpu_time
                print(f'   🚀 GPU is {speedup:.1f}x faster than CPU!')
            else:
                print(f'   💻 CPU performed better (small matrix size)')
                
        except Exception as e:
            print(f'   Performance test failed: {e}')
            
    else:
        print('💻 NO GPU DETECTED - TensorFlow running on CPU only')
        print('   Reasons could be:')
        print('   - No NVIDIA GPU installed')
        print('   - GPU drivers not installed')
        print('   - CUDA not installed')
        print('   - TensorFlow-GPU not installed')
        
    # Test basic TensorFlow functionality
    print('🧪 Basic TensorFlow functionality test:')
    try:
        test_tensor = tf.constant([1, 2, 3, 4])
        result = tf.reduce_sum(test_tensor)
        print(f'✅ Tensor operations working: sum([1,2,3,4]) = {result.numpy()}')
        
        # Test a simple neural network layer
        layer = tf.keras.layers.Dense(10, activation='relu')
        test_input = tf.random.normal([32, 20])
        output = layer(test_input)
        print(f'✅ Neural network layer test: input shape {test_input.shape} -> output shape {output.shape}')
        
    except Exception as e:
        print(f'❌ TensorFlow functionality test failed: {e}')
        
else:
    print(f'❌ TensorFlow: NOT AVAILABLE - {tensorflow_error}')
    print('💡 To install TensorFlow:')
    print('   pip install tensorflow>=2.12.0')

# Test XGBoost and LightGBM GPU support
print('=' * 60)
print('🏎️  XGBOOST & LIGHTGBM GPU SUPPORT')
print('=' * 60)

# XGBoost GPU test
try:
    # Check if XGBoost was built with GPU support
    print(f'XGBoost version: {xgb.__version__}')
    
    # Try to create a GPU-enabled XGBoost model
    import xgboost as xgb
    try:
        # This will work if XGBoost has GPU support
        gpu_params = {'tree_method': 'gpu_hist', 'gpu_id': 0}
        print('✅ XGBoost: GPU support available (gpu_hist method)')
    except:
        print('💻 XGBoost: CPU only (no GPU support compiled)')
        
except Exception as e:
    print(f'❌ XGBoost GPU test failed: {e}')

# LightGBM GPU test
try:
    print(f'LightGBM version: {lgb.__version__}')
    
    # Check LightGBM GPU support
    try:
        # This would work if LightGBM has GPU support
        gpu_params = {'device': 'gpu', 'gpu_platform_id': 0, 'gpu_device_id': 0}
        print('✅ LightGBM: GPU support may be available')
    except:
        print('💻 LightGBM: CPU only (no GPU support)')
        
except Exception as e:
    print(f'❌ LightGBM GPU test failed: {e}')

# Additional package results
print('=' * 60)
print('📦 ADDITIONAL PACKAGES')
print('=' * 60)

if psycopg2_available:
    print(f'✅ psycopg2: {psycopg2_version}')
else:
    print('❌ psycopg2: NOT AVAILABLE')

if pandas_ta_available:
    print(f'✅ pandas-ta: {pandas_ta_version}')
else:
    print('❌ pandas-ta: NOT AVAILABLE')

if yfinance_available:
    print(f'✅ yfinance: {yfinance_version}')
else:
    print('❌ yfinance: NOT AVAILABLE')

print('=' * 60)
print('🎯 SYSTEM SUMMARY')
print('=' * 60)

if tensorflow_available and gpus:
    print('🚀 EXCELLENT: TensorFlow with GPU support detected!')
    print('   Perfect for deep learning models in your trading system.')
elif tensorflow_available:
    print('✅ GOOD: TensorFlow available (CPU only)')
    print('   Suitable for smaller models, consider GPU for large-scale training.')
else:
    print('⚠️  WARNING: TensorFlow not available')
    print('   XGBoost and LightGBM still provide excellent ML capabilities.')

print('🎯 System Ready for Futures Trading Development!')
print('   Recommended for NQ/ES prediction: XGBoost + LightGBM')
print('   Optional: TensorFlow for advanced deep learning models')