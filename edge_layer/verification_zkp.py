import hashlib

def VerificationKnowledgeProof(packet):

    device_id = packet["device_id"]
    secret = packet["secret"]

    proof = hashlib.sha256((device_id + secret).encode()).hexdigest()

    print("ZKP generated:", proof)

    return proof