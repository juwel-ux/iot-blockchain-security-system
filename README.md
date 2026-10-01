<div align="center">

# 🔗 IoT Blockchain Security System

### A Multi-Layer Blockchain-Based Secure Communication System for IoT Devices

[![Python](https://img.shields.io/badge/Python-3.9-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.19-363636?style=for-the-badge&logo=solidity)](https://soliditylang.org/)
[![Ethereum](https://img.shields.io/badge/Ethereum-Ganache-3C3C3D?style=for-the-badge&logo=ethereum)](https://ethereum.org/)
[![IPFS](https://img.shields.io/badge/IPFS-Decentralized-65C2CB?style=for-the-badge&logo=ipfs)](https://ipfs.io/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066?style=for-the-badge)](https://mqtt.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**A Final Year Thesis Project**

**Author:** Md. Emdadul Haque  
**Student ID:** 23103346  
**Supervisor:** M.M. Rakibul Hasan  
**Department of Computer Science and Engineering**  
**IUBAT — International University of Business Agriculture and Technology**

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Innovation](#-key-innovation)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Installation](#-installation)
- [Running the Project](#-running-the-project)
- [API Endpoints](#-api-endpoints)
- [Performance Results](#-performance-results)
- [Research Gaps Addressed](#-research-gaps-addressed)
- [Limitations](#-limitations)
- [Future Work](#-future-work)
- [License](#-license)
- [Contact](#-contact)

---

## 🌟 Overview

The **IoT Blockchain Security System** is a novel multi-layer blockchain-based framework designed to provide **secure, decentralized, and gas fee-free communication** for Internet of Things (IoT) devices. This system addresses the critical limitations of traditional blockchain-based IoT solutions — high latency, excessive gas fees, and lack of integration between device registration and communication.

This research proposes a **five-layer architecture** that integrates device registration and secure communication into a single unified platform. The system employs **edge-based off-chain decryption**, **lightweight Zero-Knowledge Proof (ZKP)** authentication, and **IPFS-based decentralized storage** to create a fast, cost-effective, and scalable solution suitable for smart cities, healthcare monitoring, and industrial automation.

---

## ✨ Key Innovation

### 🎯 Zero Gas Fee Decryption

Unlike traditional blockchain-based IoT systems where decryption requires **0.001 ETH gas fee per operation**, our system performs decryption entirely **off-chain at the Edge Layer** using encrypted private keys stored in the Edge Queue. This results in:

- ✅ **100% gas fee savings** for decryption
- ✅ **99.85% latency reduction** (22.41 ms vs 15,000 ms)
- ✅ **33x higher throughput** (450 msg/sec vs 15 tx/sec)
- ✅ **678x speedup** in decryption time

---

## 🏗️ System Architecture

The proposed system follows a **five-layer architecture** with clear separation of concerns. Each layer operates independently and communicates via **API and MQTT protocols**.


---

## 🎯 Features

### 🌐 Five-Layer Architecture

| Layer | Function | Technology |
|-------|----------|------------|
| **Perception Layer** | Device identification, registration, and packet creation | MQTT, PySerial, Python |
| **Edge Layer** | RSA-2048 key generation, private key encryption, **zero gas fee decryption** | RSA-2048, AES-256, PBKDF2, Fernet |
| **Network Layer** | MQTT communication, 3-factor verification, peer sync | MQTT, MongoDB, ZKP |
| **Blockchain Layer** | Smart contract deployment, immutable device registry | Solidity, Ganache, Web3.py, PoA |
| **Application Layer** | Dashboard, device control panels, test visualization | Flask, HTML, CSS, Chart.js |

### 🔐 Security Features

- **End-to-End Encryption** — RSA-2048 + AES-256-GCM hybrid encryption
- **Lightweight ZKP** — Hash-based Zero-Knowledge Proof for resource-constrained IoT devices
- **Secure Key Management** — Private keys stored in Edge Queue (never on blockchain)
- **Password Protection** — PBKDF2-based key derivation (100,000 iterations)
- **Immutable Device Registry** — Smart contract on blockchain
- **IPFS Decentralized Storage** — Encrypted file and message storage

### 📱 Application Features

- **Web Dashboard** — Real-time system status monitoring
- **Device Control Panel** — Separate panel for each device
- **Message Interface** — Send/receive encrypted messages
- **File Transfer** — Drag-and-drop file upload/download
- **Auto-Store Feature** — Automatic sensor data storage
- **6 Performance Tests** — Scalability, Throughput, Latency, Registration, Encryption/Decryption, Gas Cost

---

## 🛠️ Technology Stack

### Backend

| Category | Technology |
|----------|------------|
| **Language** | Python 3.9 |
| **Framework** | Flask 2.0, Flask-CORS |
| **Blockchain** | Solidity 0.8.19, Ganache 7.0, Web3.py 5.0 |
| **Cryptography** | RSA-2048, AES-256-GCM, PBKDF2, SHA-256 |
| **Communication** | MQTT (Mosquitto), Paho-MQTT |
| **Storage** | IPFS, MongoDB, Edge Queue |
| **Frontend** | HTML5, CSS3, JavaScript, Chart.js |

---

## 📂 Project Structure
iot-blockchain-security-system/
│
├── web_app/ # Flask Web Application
│ ├── app.py
│ ├── templates/
│ └── static/
│
├── perception_layer/ # Layer 1: Device Registration
│ ├── device_selector.py
│ ├── registration_packet.py
│ └── mqtt_handler.py
│
├── edge_layer/ # Layer 2: Cryptographic Operations
│ ├── edge_gateway.py
│ ├── device_crypto.py
│ └── network_sender.py
│
├── network_layer/ # Layer 3: Communication & Verification
│ ├── verification.py
│ ├── propagation.py
│ └── sync.py
│
├── blockchain_layer/ # Layer 4: Blockchain Integration
│ ├── contracts/DeviceRegistry.sol
│ ├── ganache_client.py
│ └── web3_integration.py
│
├── ipfs_handler/ # IPFS Integration
│ └── ipfs_handler_v2.py
│
├── security/ # Security Module
│ └── zkp.py
│
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md

---

## 🔄 How It Works

### Device Registration Process (9 Steps)

1. User selects device type + sets password
2. System generates unique Virtual ID (VID)
3. Registration packet created (JSON)
4. Packet sent to Edge Layer via MQTT
5. Edge Layer receives and processes packet
6. RSA-2048 key pair generated
7. Private key encrypted → stored in Edge Queue
8. Public key verified → propagated to Network Layer
9. Device registered on Blockchain + Control Panel created

### Secure Communication Process

- **Sender:** Gets public key → Encrypts message → Uploads to IPFS → Stores CID on blockchain
- **Receiver:** Gets CID → Downloads from IPFS → Decrypts at Edge Layer → **ZERO GAS FEE**

---

## 🚀 Installation

### Prerequisites

```bash
- Python 3.9+
- Ganache 7.0+
- Mosquitto MQTT Broker
- IPFS (go-ipfs)
- MongoDB
- Git
🚀 Future Work

    Decentralized Edge Layer using Shamir's Secret Sharing

    Persistent Storage (Redis/PostgreSQL)

    Public Blockchain Deployment (Ethereum, Polygon)

    Large-Scale Testing (1000+ devices)

    Post-Quantum Cryptography (CRYSTALS-Kyber)

📄 License

This project is licensed under the MIT License — see the LICENSE file for details.
📞 Contact

Md. Emdadul Haque
Student ID: 23103346
Department of Computer Science and Engineering
IUBAT — International University of Business Agriculture and Technology
Dhaka, Bangladesh

📧 Email: emdaduljuwelj@gmail.com
🔗 GitHub: @juwel-ux
<div align="center">
⭐ If you find this project helpful, please give it a star! ⭐

Made with ❤️ using Python, Solidity, and IPFS

© 2026 Md. Emdadul Haque. All rights reserved.
</div> ```
