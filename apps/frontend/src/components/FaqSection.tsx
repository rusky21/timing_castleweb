import React from 'react';
import './FaqSection.css';

export const FaqSection: React.FC = () => {
  return (
    <section className="faq-section" id="faq">
      <div className="faq-container">
        {/* ================================================================= */}
        {/* Header: "Вопросы !?" Aligned to the Right */}
        {/* ================================================================= */}
        <div className="faq-header-row reveal-void">
          <div className="faq-title-wrap">
            <h2 className="faq-title">Вопросы</h2>
            <div className="faq-title-marks" aria-hidden="true">
              <img
                src="/faq_assets/title_blue_excl.png"
                alt="!"
                className="faq-mark-blue-excl"
              />
              <img
                src="/faq_assets/title_red_q.png"
                alt="?"
                className="faq-mark-red-q"
              />
            </div>
          </div>
        </div>

        {/* ================================================================= */}
        {/* Block 1: Tech Stack Question & Answer */}
        {/* ================================================================= */}
        <div className="faq-conversation-block faq-block-one">
          {/* Question 1 (Client, Left) */}
          <div className="faq-msg-row faq-row-left">
            <div className="faq-bubble-wrapper faq-q1-wrapper reveal-void-left">
              {/* Question Badge */}
              <div className="faq-badge faq-badge-q" aria-hidden="true">
                <span>?</span>
              </div>

              {/* Hand-drawn Doodles around Q1 */}
              <img
                src="/faq_assets/q_boxy.png"
                alt=""
                className="faq-doodle faq-doodle-boxy-q"
                aria-hidden="true"
              />
              <img
                src="/faq_assets/q_big.png"
                alt=""
                className="faq-doodle faq-doodle-big-q"
                aria-hidden="true"
              />
              <img
                src="/faq_assets/q_mid.png"
                alt=""
                className="faq-doodle faq-doodle-mid-q"
                aria-hidden="true"
              />
              <img
                src="/faq_assets/q_small.png"
                alt=""
                className="faq-doodle faq-doodle-small-q"
                aria-hidden="true"
              />

              {/* Bubble Body */}
              <div className="faq-bubble faq-bubble-question faq-q1-bubble">
                <p className="faq-text">
                  Какой стек технологий вы
                  <br />
                  используете?
                </p>
              </div>
            </div>
          </div>

          {/* Answer 1 (Studio, Right) */}
          <div className="faq-msg-row faq-row-right">
            <div className="faq-bubble-wrapper faq-a1-wrapper reveal-void-right delay-150">
              {/* Studio CS Badge */}
              <div className="faq-badge faq-badge-cs" aria-hidden="true">
                <span>CS</span>
              </div>

              {/* Yellow Smiley on top */}
              <img
                src="/faq_assets/smiley_yellow.png"
                alt=""
                className="faq-doodle faq-doodle-smiley"
                aria-hidden="true"
              />

              {/* Red Heart on bottom right */}
              <img
                src="/faq_assets/heart_red.png"
                alt=""
                className="faq-doodle faq-doodle-heart"
                aria-hidden="true"
              />

              {/* Bubble Body */}
              <div className="faq-bubble faq-bubble-answer faq-a1-bubble">
                <p className="faq-text">
                  Пишем на всём, кроме заборов. Не ограничиваем себя
                  <br />
                  одним языком, так что стек подбираем индивидуально
                  <br />— главное, чтобы код работал, а бизнес рос
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ================================================================= */}
        {/* Block 2: Process & Terms Questions + Comprehensive Studio Answer */}
        {/* ================================================================= */}
        <div className="faq-conversation-block faq-block-two">
          {/* Angry Face Hand-drawn Doodle on Far Left */}
          <div className="faq-angry-face-wrap reveal-void delay-200" aria-hidden="true">
            <img
              src="/faq_assets/angry_face.png"
              alt=""
              className="faq-doodle-angry-face"
            />
          </div>

          {/* Client Questions List (Left) */}
          <div className="faq-questions-list reveal-void-left">
            {/* Question 2 */}
            <div className="faq-question-item">
              <div className="faq-bubble-wrapper">
                <div className="faq-badge faq-badge-q" aria-hidden="true">
                  <span>?</span>
                </div>
                <div className="faq-bubble faq-bubble-question faq-q2-bubble">
                  <p className="faq-text">
                    Как формируется смета и
                    <br />
                    сроки?
                  </p>
                </div>
              </div>
              <div className="faq-item-mark" aria-hidden="true">
                <img
                  src="/faq_assets/excl_single_vert.png"
                  alt="!"
                  className="faq-doodle-excl faq-doodle-excl-vert"
                />
              </div>
            </div>

            {/* Question 3 */}
            <div className="faq-question-item">
              <div className="faq-bubble-wrapper">
                <div className="faq-badge faq-badge-q" aria-hidden="true">
                  <span>?</span>
                </div>
                <div className="faq-bubble faq-bubble-question faq-q3-bubble">
                  <p className="faq-text">Кому принадлежат исходники?</p>
                </div>
              </div>
              <div className="faq-item-mark" aria-hidden="true">
                <img
                  src="/faq_assets/excl_double.png"
                  alt="!!"
                  className="faq-doodle-excl faq-doodle-excl-double"
                />
              </div>
            </div>

            {/* Question 4 */}
            <div className="faq-question-item">
              <div className="faq-bubble-wrapper">
                <div className="faq-badge faq-badge-q" aria-hidden="true">
                  <span>?</span>
                </div>
                <div className="faq-bubble faq-bubble-question faq-q4-bubble">
                  <p className="faq-text">Как строится оплата</p>
                </div>
              </div>
              <div className="faq-item-mark" aria-hidden="true">
                <img
                  src="/faq_assets/excl_slash.png"
                  alt="! /"
                  className="faq-doodle-excl faq-doodle-excl-slash"
                />
              </div>
            </div>

            {/* Question 5 */}
            <div className="faq-question-item">
              <div className="faq-bubble-wrapper">
                <div className="faq-badge faq-badge-q" aria-hidden="true">
                  <span>?</span>
                </div>
                <div className="faq-bubble faq-bubble-question faq-q5-bubble">
                  <p className="faq-text">
                    Оказывается ли поддержка
                    <br />
                    после релиза?
                  </p>
                </div>
              </div>
              <div className="faq-item-mark" aria-hidden="true">
                <img
                  src="/faq_assets/excl_slanted.png"
                  alt="!"
                  className="faq-doodle-excl faq-doodle-excl-slanted"
                />
              </div>
            </div>
          </div>

          {/* Answer 2 (Studio, Right) */}
          <div className="faq-msg-row faq-row-right faq-a2-row">
            <div className="faq-bubble-wrapper faq-a2-wrapper reveal-void-right delay-150">
              <div className="faq-badge faq-badge-cs" aria-hidden="true">
                <span>CS</span>
              </div>
              <div className="faq-bubble faq-bubble-answer faq-a2-bubble">
                <p className="faq-text">
                  Сроки и смету считаем прозрачно, исходники на 100%
                  <br />
                  ваши, платим поэтапно по спринтам и не бросаем
                  <br />
                  после релиза — именно поэтому мы с радостью
                  <br />
                  заключим договор!
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FaqSection;
