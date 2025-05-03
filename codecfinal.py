import json
import sys
import tiktoken
import string

enc = tiktoken.get_encoding("cl100k_base")

# -----------------------------------------------------------------------------  
# ascii indexing

ALPHA   = string.ascii_uppercase + string.ascii_lowercase + string.digits

A2I     = {c: i for i, c in enumerate(ALPHA)}

I2A     = {i: c for c, i in A2I.items()}

def encode_idx(i):
    if i < len(ALPHA):
        return I2A[i]
    
    return f"_{i};"                

def decode_idx(s, pos):
    c = s[pos]
    if c != "_":
        return A2I[c], 1
    
    end = s.index(";", pos + 1)

    return int(s[pos + 1:end]), end - pos + 1

        

# ---------------------------------------------------------
# cjk single rune (chinese japanese korean)

CJK_BASE = 0x4E00
CJK_END  = 0x9FFF
CJK_CAP  = CJK_END - CJK_BASE + 1       

def edge_to_rune( u, v, n):
    code = u *n + v
    if code < CJK_CAP:                
        return chr( CJK_BASE + code )
    
    return encode_idx(u) + encode_idx(v) # two indices

def edges_from_str( edge_part, n, ids ): # list strings
    edges, pos = [], 0

    while pos < len( edge_part ):

        ch = edge_part[ pos ]

        if CJK_BASE <= ord(ch) <= CJK_END:          
            code = ord(ch) - CJK_BASE

            u, v= divmod( code, n )

            pos +=1
        else:                                      
            u, du = decode_idx(edge_part, pos) ;  pos += du

            v, dv= decode_idx(edge_part, pos );  pos += dv

        edges.append({ "u": ids[u] , "v" : ids[v] } )

    return edges




# ---------------------------------------------------------
def encode(graph: dict) -> str :
    ids   = [ n["id"] for n in graph["nodes" ] ]

    descs = [ n["desc"] for n in graph["nodes"]]

    id2ix = { i: k for k, i in enumerate(ids) }

    node_part = "|".join( f"{i}={d}" for i, d in zip(ids, descs))

    # acsii candidate
    ascii_edges = "".join( encode_idx(id2ix[ e["u"]] )+ encode_idx(id2ix[ e[ "v"] ]) for e in graph[ "edges" ])

    blob_ascii  = f"{node_part}||{ ascii_edges}" 

    # rune candidate
    n = len(ids)
    rune_edges = "".join(edge_to_rune( id2ix[ e["u"] ] , id2ix[e["v"]], n) for e in graph["edges"])

    blob_rune  = f"{ node_part }||{ rune_edges}"

    # choose best
    return blob_ascii if _token_count( blob_ascii) < _token_count(blob_rune) else blob_rune
    

def decode(blob: str) -> dict:
    node_part, edge_part = blob.split("||", 1)

    ids, descs = [], []

    for rec in node_part.split("|"):
        i, d = rec.split("=", 1)
        ids.append(i)

        descs.append(d)

    nodes = [{ "id": i, "desc": d } for i , d in zip(ids, descs)]

    edges = edges_from_str(edge_part, len(ids), ids)
    return { "nodes": nodes, "edges": edges}



# ---------- local runner ---------- #
def _token_count(s: str) -> int:
    return len(enc.encode(s))


if __name__ == "__main__":
    raw = sys.stdin.read()
    g = json.loads(raw)
    blob = encode(g)
    rebuilt = decode(blob)

    assert rebuilt == g, "round‑trip failed"
    print(blob)
    print(f"#tokens: {_token_count(blob)}", file=sys.stderr)
    #print(f"baseline JSON tokens: {_token_count(json.dumps(g, separators=(',', ':')))} tokens")