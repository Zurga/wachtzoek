var chart = c3.generate({
    bindto: '#timeline',
    data: {
        columns: [
            ['Resultaten', 30, 200, 100, 400, 150, 250, 50, 100, 250]
        ]
    },
    axis: {
        x: {
            type: 'category',
            categories: ['2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008']
        }
    }
});
