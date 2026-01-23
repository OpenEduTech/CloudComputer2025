export async function fetch_gen(concept) {
    const res = await fetch('http://localhost:8000/api/kg/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept })
    });
    const data = await res.json();
    return data;
}

export async function fetch_quick_search(concept){
    const res = await fetch('http://localhost:8000/api/kg/query-db', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept })
    });
    const data = await res.json();
    return data;
}