import React from 'react';

const groups = [
  { label: 'Entry', ids: ['frontend'] },
  { label: 'Application services', ids: ['authservice', 'cartservice', 'checkoutservice', 'paymentservice', 'productcatalogservice', 'recommendationservice', 'shippingservice'] },
  { label: 'Dependencies', ids: ['database', 'emailservice', 'currencyservice', 'adservice'] },
];

const humanize = (name) => name.replace(/service/g, ' service').replace(/^./, (letter) => letter.toUpperCase());

const TopologyMap = ({ failingNode, services = [] }) => (
  <div className="topology-map">
    {groups.map((group, index) => (
      <React.Fragment key={group.label}>
        <section className="topology-level">
          <h3>{group.label}</h3>
          <div className="topology-nodes">
            {group.ids.map((id) => {
              const service = services.find((item) => item.id === id);
              const status = service?.status || (failingNode === id ? 'down' : 'healthy');
              return <article className={`topology-node node-${status}`} key={id}><strong>{humanize(id)}</strong><span>{status}</span>{service?.dependencies?.length > 0 && <small>→ {service.dependencies.join(', ')}</small>}</article>;
            })}
          </div>
        </section>
        {index < groups.length - 1 && <div className="topology-connector" aria-hidden="true">↓</div>}
      </React.Fragment>
    ))}
  </div>
);

export default TopologyMap;
