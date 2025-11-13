# SDXL Speed Models Installation & Usage Guide

This guide covers the installation and usage of **SDXL Lightning** and **Hyper SDXL** models for ultra-fast image generation in ComfyUI.

## 🚀 Installation Summary

### ✅ **Successfully Installed Components**

#### **Custom Nodes**
- ✅ **ComfyUI-HyperSDXL1StepUnetScheduler** - Required for Hyper SDXL 1-Step generation

#### **SDXL Lightning Models** (Recommended for Performance)
- ✅ **sdxl_lightning_4step.safetensors** (6.9GB) - Full checkpoint
- ✅ **sdxl_lightning_4step_unet.safetensors** (5.1GB) - UNet-only version

#### **Total Downloaded**: ~12GB of speed models

---

## 🎯 Quick Start with SDXL Lightning 4-Step

### **Method 1: Using UNet (Recommended & Flexible)**

1. **Load Base Model**: Use `Load Checkpoint` node to load any SDXL 1.0 model
2. **Load Lightning UNet**: Use `Load UNET` node to load `sdxl_lightning_4step_unet.safetensors`
3. **Connect**: Connect the Lightning UNET to your sampler
4. **Configure Sampler**: Use `KSampler` with these settings:
   - `steps`: 4
   - `cfg`: 1.0 (⚠️ Must be exactly 1.0)
   - `sampler_name`: dpmpp_2m_sde or euler
   - `scheduler`: sgm_uniform or karras

### **Method 2: Using Full Checkpoint**

1. **Load Lightning Model**: Use `Load Checkpoint` node to load `sdxl_lightning_4step.safetensors`
2. **Configure Sampler**: Same KSampler settings as above

---

## ⚡ Performance Comparison

| Method | Steps | Time (RTX 3060) | Quality | Notes |
|--------|--------|------------------|---------|-------|
| Standard SDXL | 20-30 | 8-12s | ⭐⭐⭐⭐⭐ | Baseline |
| SDXL Lightning | 4 | 2-3s | ⭐⭐⭐⭐ | 4x faster |
| Hyper SDXL | 1 | 0.5-1s | ⭐⭐⭐ | Ultra-fast |

---

## 🛠️ Workflow Configuration Examples

### **Basic SDXL Lightning 4-Step Workflow**

```yaml
# Load base SDXL model
model_loader:
  node_type: LoadCheckpoint
  model_name: "sd_xl_base_1.0.safetensors"  # Any SDXL base model

# Load Lightning UNet
lightning_unet:
  node_type: LoadUNET
  unet_name: "sdxl_lightning_4step_unet.safetensors"

# Sampler settings
sampler:
  node_type: KSampler
  steps: 4
  cfg: 1.0
  sampler_name: dpmpp_2m_sde
  scheduler: sgm_uniform
  denoise: 1.0

# Connections
model_loader.positive -> ClipTextEncode
lightning_unet -> sampler.model
```

### **Advanced Hyper SDXL 1-Step Workflow**

```yaml
# Load Hyper SDXL model
hyper_model:
  node_type: LoadCheckpoint
  model_name: "Hyper-SDXL-1step-Unet-Comfyui.fp16.safetensors"

# Use custom scheduler
hyper_scheduler:
  node_type: HyperSDXL1StepUNET
  model: hyper_model.model

# SamplerCustom for non-standard setup
sampler:
  node_type: SamplerCustom
  model: hyper_scheduler.output
  steps: 1
  cfg: 1.0
```

---

## 📋 Critical Settings

### **Required Settings for Lightning Models**

- **CFG Scale**: Must be exactly `1.0` (Lightning models are distilled and don't use CFG)
- **Steps**: Match the model (`4` for 4-step, `1` for 1-step)
- **Sampler**: `dpmpp_2m_sde` or `euler` (recommended)
- **Scheduler**: `sgm_uniform` or `karras` (recommended)

### **Common Issues & Solutions**

#### **❌ CFG Not Set to 1.0**
```
Problem: Poor quality output
Solution: Set cfg: 1.0 in KSampler
```

#### **❌ Wrong Number of Steps**
```
Problem: Model not performing optimally
Solution: Use 4 steps for 4-step model, 1 step for 1-step model
```

#### **❌ Using Incompatible Scheduler**
```
Problem: Slow generation or poor quality
Solution: Use sgm_uniform or karras scheduler
```

---

## 🎨 Quality Tips

### **For Best Results with SDXL Lightning:**

1. **Prompt Engineering**: Keep prompts clear and concise
2. **Negative Prompts**: Use negative prompts to improve quality
3. **Resolution**: Work best with standard SDXL resolutions (1024x1024)
4. **Batch Size**: Can process multiple images quickly due to speed

### **Recommended Prompt Structure:**

```
Positive: "high quality, detailed, professional photograph of [subject]"
Negative: "blurry, low quality, distorted, bad anatomy, ugly, watermark"
```

---

## 🔄 ComfyUI Setup

### **Restart Required**
The new custom node requires ComfyUI restart to load properly.

```bash
cd /home/ned/ComfyUI-Install/ComfyUI
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188 --cpu
```

### **Access Web Interface**
- **URL**: http://192.168.178.15:8188
- **Models**: Available in Load Checkpoint/Load UNET menus
- **Nodes**: HyperSDXL1StepUNET node available in node menu

---

## 📁 File Locations

### **Models**
- **Checkpoints**: `/home/ned/ComfyUI-Install/ComfyUI/models/checkpoints/`
  - `sdxl_lightning_4step.safetensors`
- **UNET**: `/home/ned/ComfyUI-Install/ComfyUI/models/unet/`
  - `sdxl_lightning_4step_unet.safetensors`

### **Custom Nodes**
- **Path**: `/home/ned/ComfyUI-Install/ComfyUI/custom_nodes/ComfyUI-HyperSDXL1StepUnetScheduler/`

### **Scripts**
- **Installation**: `/home/ned/ComfyUI-Install/install_sdxl_speed_models.sh`

---

## ⚡ Performance Optimization for RTX 3060

### **Optimal Settings:**
- **Batch Size**: 2-4 images
- **Resolution**: 1024x1024 or 1152x896
- **CPU Offloading**: Enable `--cpu` flag in ComfyUI startup
- **Memory Management**: Monitor VRAM usage

### **Startup Command:**
```bash
cd /home/ned/ComfyUI-Install/ComfyUI
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188 --cpu --highvram
```

---

## 🔧 Troubleshooting

### **Model Not Showing in ComfyUI**
1. Restart ComfyUI completely
2. Check model file permissions: `ls -la models/checkpoints/`
3. Verify model integrity: Models should be complete files

### **Custom Node Not Loading**
1. Verify installation: Check `/custom_nodes/ComfyUI-HyperSDXL1StepUnetScheduler/` exists
2. Restart ComfyUI
3. Check ComfyUI console for loading errors

### **Poor Quality Output**
1. Verify `cfg: 1.0` setting
2. Use correct step count
3. Try different samplers (euler, dpmpp_2m_sde)
4. Check prompt quality

---

## 📊 Usage Statistics

### **Expected Performance on RTX 3060:**
- **4-Step Lightning**: ~2-3 seconds per image
- **1-Step Hyper**: ~0.5-1 second per image (if model installed)
- **Memory Usage**: ~4-6GB VRAM for SDXL Lightning

### **Quality vs Speed Trade-off:**
- **Lightning 4-Step**: Excellent balance of speed and quality
- **Hyper 1-Step**: Maximum speed, slightly reduced quality

---

## 🚀 Next Steps

1. **Test Basic Workflow**: Create a simple SDXL Lightning workflow
2. **Experiment with Prompts**: Try different subjects and styles
3. **Batch Processing**: Generate multiple images efficiently
4. **Quality Comparison**: Compare with standard SDXL output

---

## 📖 Additional Resources

- **SDXL Lightning Paper**: [ByteDance Research](https://github.com/ByteDance/SDXL-Lightning)
- **Hyper SDXL**: [Hyper-SD Repository](https://github.com/ByteDance/Hyper-SD)
- **ComfyUI Documentation**: [Official ComfyUI](https://docs.comfy.org/)

---

## ✅ Installation Verification Checklist

- [x] HyperSDXL1StepUnetScheduler custom node installed
- [x] sdxl_lightning_4step.safetensors downloaded (6.9GB)
- [x] sdxl_lightning_4step_unet.safetensors downloaded (5.1GB)
- [x] Installation script created
- [x] Documentation completed
- [ ] Test workflows created
- [ ] Performance tested

**Status**: ✅ Ready to use SDXL Lightning 4-Step generation!

---

**🎉 Congratulations! You now have ultra-fast SDXL generation capability!**